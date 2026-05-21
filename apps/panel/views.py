from functools import wraps
from datetime import date as date_type, datetime, time
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import login, logout
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone

from apps.publico.models import EstadoReclamacion, Reclamacion
from apps.viajes.models import Viaje, EstadoViaje
from apps.viajes.views import PISO_SPLITS
from apps.ventas.models import (
    Boleto,
    CancelacionBoleto,
    EstadoBoleto,
    EstadoPagoBoleto,
    ReprogramacionBoleto,
)
from apps.ventas.whatsapp import enviar_confirmacion_boleto
from apps.rutas.models import CIUDADES_ACTIVAS_DB, Ruta
from apps.flota.models import Bus
from apps.cuentas.models import RolUsuario, Usuario
from apps.cuentas.forms import FormularioLogin
from apps.encomiendas.models import Encomienda, EstadoEncomienda
from apps.panel.forms import (
    FormularioRegistroUsuarioSistema,
    FormularioTrabajadorEmpresa,
    PermisoSistemaForm,
    RolSistemaForm,
    VenderBoletoPanelForm,
    ViajePanelForm,
)
from apps.panel.models import PermisoSistema, RolSistema, TrabajadorEmpresa

# ── Roles permitidos en el panel ──────────────────────────────────────────────
ROLES_PANEL = frozenset({
    'admin',
    'vendedor',
    'encomiendas',
    'conductor',
    'admin_empresa',
    'super_admin',
})


# ── Decorador de protección ───────────────────────────────────────────────────
def panel_required(view_func):
    """Redirige a /panel/login/ si no está autenticado o si no tiene rol de trabajador."""
    @wraps(view_func)
    @never_cache
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('panel:login')
        if request.user.rol not in ROLES_PANEL:
            # Cliente que intentó entrar al panel → lo regresamos al inicio
            return redirect('publico:inicio')
        return view_func(request, *args, **kwargs)
    return wrapper


# ── Login del panel ───────────────────────────────────────────────────────────
def usuario_tiene_permiso(usuario, codigo_permiso):
    if RolSistema.objects.filter(
        codigo=usuario.rol,
        activo=True,
        permisos__codigo=codigo_permiso,
        permisos__activo=True,
    ).exists():
        return True
    return usuario.permisos.filter(codigo=codigo_permiso, activo=True).exists()


def permiso_panel_required(codigo_permiso):
    def decorator(view_func):
        @panel_required
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not usuario_tiene_permiso(request.user, codigo_permiso):
                messages.error(request, 'No tienes permiso para acceder a este modulo.')
                return redirect('panel:dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


@never_cache
def vista_login_panel(request):
    """Login exclusivo para trabajadores y administradores en /panel/login/."""
    if request.user.is_authenticated:
        if request.user.rol in ROLES_PANEL:
            return redirect('panel:dashboard')
        return redirect('publico:inicio')

    error_rol = None
    form = FormularioLogin(request.POST or None, request=request)

    if request.method == 'POST' and form.is_valid():
        user = form.usuario_autenticado
        if user.rol not in ROLES_PANEL:
            error_rol = (
                'Esta área es exclusiva para trabajadores y administradores. '
                'Si eres pasajero, compra tu pasaje desde el sitio web.'
            )
        else:
            login(request, user)
            return redirect('panel:dashboard')

    return render(request, 'panel/login.html', {'form': form, 'error_rol': error_rol})


# ── Vistas protegidas ─────────────────────────────────────────────────────────
@panel_required
def dashboard(request):
    actualizar_estados_viajes()
    hoy = timezone.localdate()
    inicio_hoy = timezone.make_aware(datetime.combine(hoy, time.min))
    fin_hoy    = timezone.make_aware(datetime.combine(hoy + timezone.timedelta(days=1), time.min))

    # ── Métricas diarias ──────────────────────────────────────────────
    boletos_hoy_qs = Boleto.objects.filter(
        fecha_compra__gte=inicio_hoy,
        fecha_compra__lt=fin_hoy,
        estado=EstadoBoleto.CONFIRMADO,
    )
    ventas_hoy = boletos_hoy_qs.aggregate(total=Sum('precio_pagado'))['total'] or Decimal('0.00')
    boletos_hoy = boletos_hoy_qs.count()

    encomiendas_hoy_qs = Encomienda.objects.filter(
        creado_en__gte=inicio_hoy,
        creado_en__lt=fin_hoy,
    ).exclude(estado=EstadoEncomienda.CANCELADO)
    encomiendas_hoy = encomiendas_hoy_qs.count()

    pendientes_entrega = Encomienda.objects.filter(
        estado__in=[EstadoEncomienda.EN_AGENCIA_DESTINO],
    ).count()

    viajes_proximos = Viaje.objects.filter(
        fecha_salida__gte=timezone.now(),
        estado__in=[EstadoViaje.PROGRAMADO, EstadoViaje.EN_EMBARQUE],
        ruta__activo=True,
        ruta__origen__in=CIUDADES_ACTIVAS_DB,
        ruta__destino__in=CIUDADES_ACTIVAS_DB,
    ).count()

    pagos_pendientes = Boleto.objects.filter(
        estado_pago=EstadoPagoBoleto.PENDIENTE,
        estado=EstadoBoleto.CONFIRMADO,
    ).aggregate(total=Sum('precio_pagado'))['total'] or Decimal('0.00')

    encomiendas_transito = Encomienda.objects.filter(
        estado=EstadoEncomienda.EN_TRANSITO,
    ).count()

    alertas = (
        Boleto.objects.filter(estado=EstadoBoleto.PENDIENTE).count()
        + Encomienda.objects.filter(
            estado=EstadoEncomienda.REGISTRADO,
            creado_en__gte=inicio_hoy,
            creado_en__lt=fin_hoy,
        ).count()
    )

    # ── Próximas salidas ──────────────────────────────────────────────
    proximas_salidas = Viaje.objects.filter(
        fecha_salida__gte=timezone.now(),
        estado__in=[EstadoViaje.PROGRAMADO, EstadoViaje.EN_EMBARQUE],
        ruta__activo=True,
        ruta__origen__in=CIUDADES_ACTIVAS_DB,
        ruta__destino__in=CIUDADES_ACTIVAS_DB,
    ).select_related('ruta', 'bus').order_by('fecha_salida')[:3]

    # ── Últimas ventas (las más recientes del sistema) ────────────────
    ultimas_ventas_boletos = list(
        Boleto.objects.filter(
            estado=EstadoBoleto.CONFIRMADO,
        ).select_related('viaje__ruta').order_by('-fecha_compra')[:5]
    )
    ultimas_encomiendas = list(
        Encomienda.objects.exclude(
            estado=EstadoEncomienda.CANCELADO,
        ).order_by('-creado_en')[:5]
    )
    ultimas_ventas = sorted(
        [{'tipo': 'boleto', 'obj': b, 'fecha': b.fecha_compra} for b in ultimas_ventas_boletos]
        + [{'tipo': 'encomienda', 'obj': e, 'fecha': e.creado_en} for e in ultimas_encomiendas],
        key=lambda x: x['fecha'],
        reverse=True,
    )[:3]

    # ── Pendientes importantes ─────────────────────────────────────────
    enc_por_entregar  = Encomienda.objects.filter(estado=EstadoEncomienda.EN_AGENCIA_DESTINO).count()
    pagos_pend_count  = Boleto.objects.filter(estado_pago=EstadoPagoBoleto.PENDIENTE, estado=EstadoBoleto.CONFIRMADO).count()
    viajes_confirmar  = Viaje.objects.filter(
        estado=EstadoViaje.PROGRAMADO,
        fecha_salida__gte=timezone.now(),
        ruta__activo=True,
    ).count()

    contexto = {
        'hoy': hoy,
        # tarjetas
        'ventas_hoy':          ventas_hoy,
        'boletos_hoy':         boletos_hoy,
        'encomiendas_hoy':     encomiendas_hoy,
        'pendientes_entrega':  pendientes_entrega,
        'viajes_proximos':     viajes_proximos,
        'pagos_pendientes':    pagos_pendientes,
        'encomiendas_transito': encomiendas_transito,
        'alertas':             alertas,
        # secciones inferiores
        'proximas_salidas':    proximas_salidas,
        'ultimas_ventas':      ultimas_ventas,
        'enc_por_entregar':    enc_por_entregar,
        'pagos_pend_count':    pagos_pend_count,
        'viajes_confirmar':    viajes_confirmar,
    }
    return render(request, 'panel/dashboard.html', contexto)


def _filtrar_por_empresa_viajes(qs, usuario):
    if usuario.rol != RolUsuario.SUPER_ADMIN and usuario.empresa:
        return qs.filter(bus__empresa=usuario.empresa)
    return qs


def _filtrar_por_empresa_boletos(qs, usuario):
    if usuario.rol != RolUsuario.SUPER_ADMIN and usuario.empresa:
        return qs.filter(viaje__bus__empresa=usuario.empresa)
    return qs


def estado_automatico_viaje(viaje, ahora=None):
    return viaje.calcular_estado_operativo(ahora)


def actualizar_estados_viajes():
    ahora = timezone.now()
    viajes_qs = Viaje.objects.exclude(estado=EstadoViaje.CANCELADO).filter(
        estado__in=[
            EstadoViaje.PROGRAMADO,
            EstadoViaje.EN_EMBARQUE,
            EstadoViaje.EN_CAMINO,
            EstadoViaje.EN_CURSO,
            EstadoViaje.COMPLETADO,
        ]
    )
    for viaje in viajes_qs.only('id', 'estado', 'fecha_salida', 'fecha_llegada_estimada'):
        nuevo_estado = estado_automatico_viaje(viaje, ahora)
        if viaje.estado != nuevo_estado:
            Viaje.objects.filter(id=viaje.id).update(estado=nuevo_estado)


def _estado_boleto_libera_asiento(estado):
    return estado in {EstadoBoleto.CANCELADO, EstadoBoleto.ANULADO, EstadoBoleto.REPROGRAMADO}


@panel_required
def viajes(request):
    actualizar_estados_viajes()
    hoy = timezone.localdate()
    fecha_limite = hoy
    inicio_rango = timezone.make_aware(datetime.combine(hoy, time.min))
    fin_rango = timezone.make_aware(datetime.combine(fecha_limite + timezone.timedelta(days=1), time.min))
    qs = (
        Viaje.objects
        .filter(
            fecha_salida__gte=inicio_rango,
            fecha_salida__lt=fin_rango,
            ruta__activo=True,
            ruta__origen__in=CIUDADES_ACTIVAS_DB,
            ruta__destino__in=CIUDADES_ACTIVAS_DB,
        )
        .select_related('ruta', 'bus', 'bus__empresa')
        .order_by('fecha_salida')
    )
    qs = _filtrar_por_empresa_viajes(qs, request.user)

    estado = request.GET.get('estado', '').strip()
    if estado:
        qs = qs.filter(estado=estado)

    fecha = request.GET.get('fecha', '').strip()
    if fecha:
        try:
            qs = qs.filter(fecha_salida__date=date_type.fromisoformat(fecha))
        except ValueError:
            fecha = ''

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(ruta__origen__icontains=q)
            | Q(ruta__destino__icontains=q)
            | Q(bus__placa__icontains=q)
            | Q(bus__empresa__nombre__icontains=q)
        )

    return render(request, 'panel/viajes.html', {
        'viajes': qs[:200],
        'estado_choices': EstadoViaje.choices,
        'estado_filtro': estado,
        'fecha_filtro': fecha,
        'hoy': hoy,
        'fecha_limite': fecha_limite,
        'q': q,
    })


@panel_required
def viaje_nuevo(request):
    form = ViajePanelForm(request.POST or None, creado_por=request.user)
    if request.method == 'POST' and form.is_valid():
        viaje = form.save()
        messages.success(request, 'Viaje programado correctamente.')
        return redirect('panel:viaje_detalle', viaje_id=viaje.id)
    return render(request, 'panel/viaje_form.html', {'form': form, 'modo': 'nuevo'})


@panel_required
def viaje_editar(request, viaje_id):
    viaje = get_object_or_404(Viaje.objects.select_related('bus', 'bus__empresa'), id=viaje_id)
    if request.user.rol != RolUsuario.SUPER_ADMIN and request.user.empresa and viaje.bus.empresa_id != request.user.empresa_id:
        return redirect('panel:viajes')
    if viaje.estado_operativo in {EstadoViaje.EN_CAMINO, EstadoViaje.FINALIZADO, EstadoViaje.CANCELADO}:
        messages.error(request, 'No se puede editar un viaje en camino, finalizado o cancelado.')
        return redirect('panel:viaje_detalle', viaje_id=viaje.id)

    form = ViajePanelForm(request.POST or None, instance=viaje, creado_por=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Viaje actualizado correctamente.')
        return redirect('panel:viaje_detalle', viaje_id=viaje.id)
    return render(request, 'panel/viaje_form.html', {'form': form, 'modo': 'editar', 'viaje': viaje})


@panel_required
def viaje_detalle(request, viaje_id):
    actualizar_estados_viajes()
    viaje = get_object_or_404(
        Viaje.objects.select_related('ruta', 'bus', 'bus__empresa'),
        id=viaje_id,
    )
    if request.user.rol != RolUsuario.SUPER_ADMIN and request.user.empresa and viaje.bus.empresa_id != request.user.empresa_id:
        return redirect('panel:viajes')

    boletos_confirmados = viaje.boletos.filter(estado=EstadoBoleto.CONFIRMADO).count()
    boletos_vendidos = viaje.boletos.exclude(
        estado__in=[EstadoBoleto.CANCELADO, EstadoBoleto.ANULADO, EstadoBoleto.REPROGRAMADO]
    ).count()
    return render(request, 'panel/viaje_detalle.html', {
        'viaje': viaje,
        'boletos_confirmados': boletos_confirmados,
        'boletos_vendidos': boletos_vendidos,
    })


@panel_required
@require_POST
def viaje_cancelar(request, viaje_id):
    actualizar_estados_viajes()
    viaje = get_object_or_404(Viaje.objects.select_related('bus', 'bus__empresa'), id=viaje_id)
    if request.user.rol != RolUsuario.SUPER_ADMIN and request.user.empresa and viaje.bus.empresa_id != request.user.empresa_id:
        return redirect('panel:viajes')
    if viaje.estado_operativo not in {EstadoViaje.FINALIZADO, EstadoViaje.CANCELADO, EstadoViaje.COMPLETADO}:
        viaje.estado = EstadoViaje.CANCELADO
        viaje.save(update_fields=['estado'])
        messages.success(request, 'Viaje cancelado correctamente.')
    return redirect('panel:viajes')


@panel_required
def viaje_boletos(request, viaje_id):
    viaje = get_object_or_404(
        Viaje.objects.select_related('ruta', 'bus', 'bus__empresa'),
        id=viaje_id,
    )
    if request.user.rol != RolUsuario.SUPER_ADMIN and request.user.empresa and viaje.bus.empresa_id != request.user.empresa_id:
        return redirect('panel:viajes')

    boletos_qs = viaje.boletos.select_related('pasajero').order_by('numero_asiento')
    estado = request.GET.get('estado', '').strip()
    if estado:
        boletos_qs = boletos_qs.filter(estado=estado)

    return render(request, 'panel/viaje_boletos.html', {
        'viaje': viaje,
        'boletos': boletos_qs,
        'estado_choices': EstadoBoleto.choices,
        'estado_filtro': estado,
    })


@panel_required
def boletos(request):
    actualizar_estados_viajes()
    qs = (
        Boleto.objects
        .select_related('viaje', 'viaje__ruta', 'viaje__bus', 'viaje__bus__empresa', 'pasajero')
        .order_by('-fecha_compra')
    )

    qs = _filtrar_por_empresa_boletos(qs, request.user)
    qs = qs.filter(viaje__fecha_salida__gte=timezone.now())

    estado_filtro = request.GET.get('estado', '').strip()
    fecha_filtro  = request.GET.get('fecha', '').strip()

    if estado_filtro:
        qs = qs.filter(estado=estado_filtro)
    if fecha_filtro:
        try:
            f = date_type.fromisoformat(fecha_filtro)
            qs = qs.filter(viaje__fecha_salida__date=f)
        except ValueError:
            fecha_filtro = ''

    viajes_para_chofer = (
        Viaje.objects
        .filter(
            boletos__estado=EstadoBoleto.CONFIRMADO,
            fecha_salida__gte=timezone.now(),
            ruta__activo=True,
            ruta__origen__in=CIUDADES_ACTIVAS_DB,
            ruta__destino__in=CIUDADES_ACTIVAS_DB,
        )
        .select_related('ruta', 'bus', 'bus__empresa')
        .distinct()
        .order_by('fecha_salida')
    )
    viajes_para_chofer = _filtrar_por_empresa_viajes(viajes_para_chofer, request.user)

    viajes_disponibles = (
        Viaje.objects
        .filter(
            estado__in=[EstadoViaje.PROGRAMADO, EstadoViaje.EN_EMBARQUE],
            fecha_salida__gte=timezone.now(),
            ruta__activo=True,
            ruta__origen__in=CIUDADES_ACTIVAS_DB,
            ruta__destino__in=CIUDADES_ACTIVAS_DB,
        )
        .select_related('ruta', 'bus', 'bus__empresa')
        .order_by('fecha_salida')
    )
    viajes_disponibles = _filtrar_por_empresa_viajes(viajes_disponibles, request.user)

    return render(request, 'panel/boletos.html', {
        'boletos':        list(qs[:200]),
        'estado_filtro':  estado_filtro,
        'fecha_filtro':   fecha_filtro,
        'estado_choices': EstadoBoleto.choices,
        'viajes_disponibles': viajes_disponibles[:80],
        'viajes_para_chofer': viajes_para_chofer[:80],
    })


@panel_required
def vender_boleto(request):
    actualizar_estados_viajes()
    viaje_id = request.GET.get('viaje') or request.POST.get('viaje')
    viaje_seleccionado = None
    ocupados = []
    asientos = []

    initial = {}
    if viaje_id:
        viaje_seleccionado = get_object_or_404(
            Viaje.objects.select_related('ruta', 'bus', 'bus__empresa'),
            id=viaje_id,
            ruta__activo=True,
            ruta__origen__in=CIUDADES_ACTIVAS_DB,
            ruta__destino__in=CIUDADES_ACTIVAS_DB,
        )
        if request.user.rol != RolUsuario.SUPER_ADMIN and request.user.empresa and viaje_seleccionado.bus.empresa_id != request.user.empresa_id:
            return redirect('panel:vender_boleto')
        initial = {
            'viaje': viaje_seleccionado,
            'monto_pagado': viaje_seleccionado.precio,
            'estado_pago': EstadoPagoBoleto.CONFIRMADO,
        }

    form = VenderBoletoPanelForm(
        request.POST or None,
        initial=initial,
        creado_por=request.user,
    )

    if viaje_seleccionado:
        ocupados = list(
            viaje_seleccionado.boletos
            .exclude(estado__in=[EstadoBoleto.CANCELADO, EstadoBoleto.ANULADO, EstadoBoleto.REPROGRAMADO])
            .values_list('numero_asiento', flat=True)
        )
        asientos = range(1, viaje_seleccionado.bus.capacidad + 1)

    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            viaje = Viaje.objects.select_for_update().select_related('bus').get(id=form.cleaned_data['viaje'].id)
            asiento = form.cleaned_data['numero_asiento']
            ocupado = Boleto.objects.select_for_update().filter(
                viaje=viaje,
                numero_asiento=asiento,
            ).exclude(
                estado__in=[EstadoBoleto.CANCELADO, EstadoBoleto.ANULADO, EstadoBoleto.REPROGRAMADO]
            ).exists()
            if ocupado:
                messages.error(request, 'El asiento fue tomado por otra venta. Selecciona otro.')
                return redirect(f'{request.path}?viaje={viaje.id}')

            estado_boleto = (
                EstadoBoleto.CONFIRMADO
                if form.cleaned_data['estado_pago'] == EstadoPagoBoleto.CONFIRMADO
                else EstadoBoleto.PENDIENTE
            )
            boleto = Boleto.objects.create(
                viaje=viaje,
                numero_asiento=asiento,
                estado=estado_boleto,
                precio_pagado=form.cleaned_data['monto_pagado'],
                tipo_doc='DNI',
                num_doc=form.cleaned_data['dni'],
                nombre_pasajero=form.cleaned_data['nombres'],
                apellido_pasajero=form.cleaned_data['apellidos'],
                email_pasajero=form.cleaned_data['correo'],
                telefono_pasajero=form.cleaned_data['telefono'],
                metodo_pago=form.cleaned_data['metodo_pago'],
                estado_pago=form.cleaned_data['estado_pago'],
                vendido_por=request.user,
            )
        if boleto.estado == EstadoBoleto.CONFIRMADO and boleto.telefono_pasajero:
            enviar_confirmacion_boleto(boleto)
        messages.success(request, f'Boleto vendido correctamente. Codigo: {str(boleto.codigo_boleto)[:8].upper()}')
        return redirect('panel:boleto_detalle', boleto_id=boleto.id)

    return render(request, 'panel/vender_boleto.html', {
        'form': form,
        'viaje_seleccionado': viaje_seleccionado,
        'ocupados': ocupados,
        'asientos': asientos,
    })


@panel_required
def boleto_detalle(request, boleto_id):
    boleto = get_object_or_404(
        Boleto.objects.select_related('viaje', 'viaje__ruta', 'viaje__bus', 'viaje__bus__empresa', 'vendido_por'),
        id=boleto_id,
    )
    qs = _filtrar_por_empresa_boletos(Boleto.objects.filter(id=boleto.id), request.user)
    if not qs.exists():
        return redirect('panel:boletos')

    if boleto.viaje.fecha_salida <= timezone.now():
        messages.error(request, 'No se puede cancelar un boleto de un viaje que ya paso o que ya inicio.')
        return redirect('panel:boletos')
    return render(request, 'panel/boleto_detalle.html', {'boleto': boleto})


@panel_required
@require_POST
def cancelar_boleto(request, boleto_id):
    boleto = get_object_or_404(Boleto.objects.select_related('viaje', 'viaje__bus', 'viaje__bus__empresa'), id=boleto_id)
    qs = _filtrar_por_empresa_boletos(Boleto.objects.filter(id=boleto.id), request.user)
    if not qs.exists():
        return redirect('panel:boletos')

    motivo = request.POST.get('motivo', '').strip() or 'Cancelacion desde panel'
    monto_devuelto = request.POST.get('monto_devuelto', '').strip()
    try:
        monto = Decimal(monto_devuelto) if monto_devuelto else None
    except Exception:
        monto = None

    if boleto.estado not in {EstadoBoleto.CANCELADO, EstadoBoleto.ANULADO, EstadoBoleto.REPROGRAMADO}:
        CancelacionBoleto.objects.create(
            boleto=boleto,
            pasajero_nombre=boleto.pasajero_nombre_completo,
            motivo=motivo,
            usuario=request.user,
            monto_devuelto=monto,
            observacion=request.POST.get('observacion', '').strip(),
        )
        boleto.estado = EstadoBoleto.CANCELADO
        boleto.save(update_fields=['estado'])
        messages.success(request, 'Boleto cancelado y asiento liberado.')
    return redirect('panel:boletos')


@panel_required
def reprogramar_boleto(request, boleto_id):
    actualizar_estados_viajes()
    boleto = get_object_or_404(
        Boleto.objects.select_related('viaje', 'viaje__ruta', 'viaje__bus', 'viaje__bus__empresa'),
        id=boleto_id,
    )
    qs = _filtrar_por_empresa_boletos(Boleto.objects.filter(id=boleto.id), request.user)
    if not qs.exists():
        return redirect('panel:boletos')

    limite_reprogramacion = boleto.viaje.fecha_salida - timezone.timedelta(hours=8)
    puede_reprogramar = timezone.now() <= limite_reprogramacion

    viajes = Viaje.objects.filter(
        ruta=boleto.viaje.ruta,
        estado__in=[EstadoViaje.PROGRAMADO, EstadoViaje.EN_EMBARQUE],
        ruta__activo=True,
        ruta__origen__in=CIUDADES_ACTIVAS_DB,
        ruta__destino__in=CIUDADES_ACTIVAS_DB,
    ).exclude(id=boleto.viaje_id).select_related('ruta', 'bus', 'bus__empresa').order_by('fecha_salida')
    viajes = _filtrar_por_empresa_viajes(viajes, request.user)

    viaje_nuevo = None
    ocupados = []
    asientos = []
    viaje_id = request.GET.get('viaje') or request.POST.get('viaje_nuevo')
    asiento_seleccionado = None
    try:
        asiento_seleccionado = int(request.POST.get('asiento_nuevo') or 0) or None
    except (TypeError, ValueError):
        asiento_seleccionado = None
    if viaje_id:
        viaje_nuevo = get_object_or_404(viajes, id=viaje_id)
        ocupados = list(
            viaje_nuevo.boletos
            .exclude(estado__in=[EstadoBoleto.CANCELADO, EstadoBoleto.ANULADO, EstadoBoleto.REPROGRAMADO])
            .values_list('numero_asiento', flat=True)
        )
        asientos = range(1, viaje_nuevo.bus.capacidad + 1)

    if request.method == 'POST':
        if not puede_reprogramar:
            messages.error(request, 'La reprogramacion solo se permite con 8 a 10 horas de anticipacion antes del viaje.')
            return redirect('panel:boleto_detalle', boleto_id=boleto.id)
        asiento_nuevo = asiento_seleccionado or 0
        if not viaje_nuevo or asiento_nuevo < 1 or asiento_nuevo > viaje_nuevo.bus.capacidad or asiento_nuevo in ocupados:
            messages.error(request, 'Selecciona un viaje y asiento disponible.')
        else:
            with transaction.atomic():
                anterior = boleto.viaje
                asiento_anterior = boleto.numero_asiento
                boleto.viaje = viaje_nuevo
                boleto.numero_asiento = asiento_nuevo
                boleto.estado = EstadoBoleto.CONFIRMADO
                boleto.precio_pagado = viaje_nuevo.precio
                boleto.save(update_fields=['viaje', 'numero_asiento', 'estado', 'precio_pagado'])
                ReprogramacionBoleto.objects.create(
                    boleto=boleto,
                    viaje_anterior=anterior,
                    viaje_nuevo=viaje_nuevo,
                    asiento_anterior=asiento_anterior,
                    asiento_nuevo=asiento_nuevo,
                    usuario=request.user,
                    motivo=request.POST.get('motivo', '').strip(),
                )
            messages.success(request, 'Boleto reprogramado sin duplicar la venta.')
            return redirect('panel:boleto_detalle', boleto_id=boleto.id)

    return render(request, 'panel/reprogramar_boleto.html', {
        'boleto': boleto,
        'viajes': viajes[:100],
        'viaje_nuevo': viaje_nuevo,
        'ocupados': ocupados,
        'asientos': asientos,
        'asiento_seleccionado': asiento_seleccionado,
        'puede_reprogramar': puede_reprogramar,
        'limite_reprogramacion': limite_reprogramacion,
    })


def _pdf_escape(texto):
    return str(texto).replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def _generar_pdf_simple(lineas, filas):
    y = 790
    contenido = ['BT', '/F1 16 Tf', f'1 0 0 1 50 {y} Tm ({_pdf_escape(lineas[0])}) Tj']
    y -= 26
    contenido.append('/F1 9 Tf')
    for linea in lineas[1:]:
        contenido.append(f'1 0 0 1 50 {y} Tm ({_pdf_escape(linea)}) Tj')
        y -= 14
    y -= 10
    contenido.append('/F1 8 Tf')
    encabezados = ['N', 'Codigo', 'DNI', 'Pasajero', 'Tel.', 'Asiento', 'Estado', 'Subio', 'Obs.']
    columnas = [50, 70, 130, 185, 310, 365, 410, 465, 510]
    for x, texto in zip(columnas, encabezados):
        contenido.append(f'1 0 0 1 {x} {y} Tm ({_pdf_escape(texto)}) Tj')
    y -= 14
    for fila in filas[:38]:
        valores = [
            fila['n'],
            fila['codigo'],
            fila['dni'],
            fila['pasajero'][:24],
            fila['telefono'][:10],
            fila['asiento'],
            fila['estado'],
            '',
            '',
        ]
        for x, texto in zip(columnas, valores):
            contenido.append(f'1 0 0 1 {x} {y} Tm ({_pdf_escape(texto)}) Tj')
        y -= 13
        if y < 60:
            break
    contenido.append('/F1 8 Tf')
    contenido.append(f'1 0 0 1 50 34 Tm ({_pdf_escape("Linea Imperial - Control de embarque")}) Tj')
    contenido.append('ET')
    stream = '\n'.join(contenido).encode('latin-1', errors='replace')

    objetos = []
    objetos.append(b'1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n')
    objetos.append(b'2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n')
    objetos.append(b'3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n')
    objetos.append(b'4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n')
    objetos.append(b'5 0 obj << /Length ' + str(len(stream)).encode() + b' >> stream\n' + stream + b'\nendstream endobj\n')
    pdf = BytesIO()
    pdf.write(b'%PDF-1.4\n')
    offsets = [0]
    for obj in objetos:
        offsets.append(pdf.tell())
        pdf.write(obj)
    xref = pdf.tell()
    pdf.write(f'xref\n0 {len(objetos) + 1}\n'.encode())
    pdf.write(b'0000000000 65535 f \n')
    for offset in offsets[1:]:
        pdf.write(f'{offset:010d} 00000 n \n'.encode())
    pdf.write(f'trailer << /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF'.encode())
    return pdf.getvalue()


@panel_required
def generar_pdf_pasajeros(request, viaje_id):
    viaje = get_object_or_404(
        Viaje.objects.select_related('ruta', 'bus', 'bus__empresa'),
        id=viaje_id,
    )
    if request.user.rol != RolUsuario.SUPER_ADMIN and request.user.empresa and viaje.bus.empresa_id != request.user.empresa_id:
        return redirect('panel:viajes')

    boletos = list(viaje.boletos.filter(estado=EstadoBoleto.CONFIRMADO).order_by('numero_asiento'))
    lineas = [
        'Linea Imperial - Lista de embarque',
        f'Empresa: {viaje.bus.empresa}',
        f'Ruta: {viaje.ruta.origen} -> {viaje.ruta.destino}',
        f'Fecha: {viaje.fecha_salida:%d/%m/%Y}  Salida: {viaje.fecha_salida:%H:%M}  Llegada: {viaje.fecha_llegada_estimada:%H:%M}',
        f'Bus: {viaje.bus.placa}  Servicio: {viaje.bus.get_tipo_servicio_display()}',
        f'Total pasajeros confirmados: {len(boletos)}',
        f'Generado: {timezone.localtime():%d/%m/%Y %H:%M}',
    ]
    filas = [
        {
            'n': str(idx),
            'codigo': str(b.codigo_boleto)[:8].upper(),
            'dni': b.num_doc,
            'pasajero': b.pasajero_nombre_completo,
            'telefono': b.telefono_pasajero,
            'asiento': str(b.numero_asiento),
            'estado': b.get_estado_display(),
        }
        for idx, b in enumerate(boletos, 1)
    ]
    response = HttpResponse(_generar_pdf_simple(lineas, filas), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="lista-embarque-viaje-{viaje.id}.pdf"'
    return response


@panel_required
def reportes(request):
    return render(request, 'panel/reportes.html')


@panel_required
def auditoria(request):
    hoy = timezone.localdate()
    try:
        anio = int(request.GET.get('anio', hoy.year))
        mes = int(request.GET.get('mes', hoy.month))
    except ValueError:
        anio = hoy.year
        mes = hoy.month

    boletos_qs = (
        Boleto.objects
        .filter(viaje__fecha_salida__lt=timezone.now())
        .select_related('viaje', 'viaje__ruta', 'viaje__bus', 'viaje__bus__empresa', 'pasajero', 'vendido_por')
        .order_by('-viaje__fecha_salida', '-fecha_compra')
    )
    boletos_qs = _filtrar_por_empresa_boletos(boletos_qs, request.user)
    boletos_qs = boletos_qs.filter(viaje__fecha_salida__year=anio, viaje__fecha_salida__month=mes)

    estado = request.GET.get('estado', '').strip()
    if estado:
        boletos_qs = boletos_qs.filter(estado=estado)

    boletos_mes = list(boletos_qs[:500])
    ingresos = boletos_qs.filter(estado=EstadoBoleto.CONFIRMADO).aggregate(total=Sum('precio_pagado'))['total'] or Decimal('0.00')

    return render(request, 'panel/auditoria.html', {
        'boletos': boletos_mes,
        'estado_choices': EstadoBoleto.choices,
        'estado_filtro': estado,
        'anio': anio,
        'mes': mes,
        'ingresos': ingresos,
        'total_boletos': boletos_qs.count(),
    })


def es_administrador_panel(usuario):
    return usuario.rol in {RolUsuario.ADMIN, RolUsuario.ADMIN_EMPRESA, RolUsuario.SUPER_ADMIN}


@panel_required
def libro_reclamaciones_panel(request):
    if not es_administrador_panel(request.user):
        messages.error(request, 'No tienes permiso para acceder al Libro de Reclamaciones.')
        return redirect('panel:dashboard')

    reclamos = Reclamacion.objects.all().order_by('-creado_en')

    q = request.GET.get('q', '').strip()
    if q:
        reclamos = reclamos.filter(
            Q(codigo__icontains=q)
            | Q(nombres_apellidos__icontains=q)
            | Q(documento__icontains=q)
            | Q(email__icontains=q)
            | Q(numero_referencia__icontains=q)
        )

    estado = request.GET.get('estado', '').strip()
    estados_validos = {value for value, _ in EstadoReclamacion.choices}
    if estado in estados_validos:
        reclamos = reclamos.filter(estado=estado)
    else:
        estado = ''

    return render(request, 'panel/libro_reclamaciones.html', {
        'reclamos': reclamos[:200],
        'estado_choices': EstadoReclamacion.choices,
        'estado_filtro': estado,
        'q': q,
        'total_pendientes': Reclamacion.objects.filter(estado=EstadoReclamacion.PENDIENTE).count(),
        'total_revision': Reclamacion.objects.filter(estado=EstadoReclamacion.EN_REVISION).count(),
        'total_respondidos': Reclamacion.objects.filter(estado=EstadoReclamacion.RESPONDIDO).count(),
        'total_cerrados': Reclamacion.objects.filter(estado=EstadoReclamacion.CERRADO).count(),
    })


@panel_required
@require_POST
def cambiar_estado_reclamacion(request, reclamacion_id):
    if not es_administrador_panel(request.user):
        messages.error(request, 'No tienes permiso para actualizar reclamos.')
        return redirect('panel:dashboard')

    reclamacion = get_object_or_404(Reclamacion, id=reclamacion_id)
    nuevo_estado = request.POST.get('estado', '')
    estados_validos = {value for value, _ in EstadoReclamacion.choices}

    if nuevo_estado in estados_validos:
        reclamacion.estado = nuevo_estado
        reclamacion.respuesta_admin = request.POST.get('respuesta_admin', '').strip()
        reclamacion.save(update_fields=['estado', 'respuesta_admin', 'actualizado_en'])
        messages.success(request, f'Estado actualizado para {reclamacion.codigo}.')

    return redirect('panel:libro_reclamaciones')


def roles_permisos_configurados():
    roles = (
        RolSistema.objects
        .filter(codigo__in=[
            RolUsuario.ADMIN,
            RolUsuario.VENDEDOR,
            RolUsuario.ENCOMIENDAS,
            RolUsuario.CONDUCTOR,
        ])
        .prefetch_related('permisos')
        .order_by('nombre')
    )
    return [
        {
            'rol': rol.codigo,
            'nombre': rol.nombre,
            'descripcion': rol.descripcion,
            'activo': rol.activo,
            'permisos': rol.permisos.filter(activo=True).order_by('modulo', 'nombre'),
        }
        for rol in roles
    ]


@permiso_panel_required('registrar_usuarios')
def registrar_usuario(request):
    form = FormularioRegistroUsuarioSistema(request.POST or None, creado_por=request.user)

    if request.method == 'POST' and form.is_valid():
        usuario = form.save()
        messages.success(
            request,
            f'Usuario {usuario.nombre_completo} registrado como {usuario.get_rol_display()}.',
        )
        return redirect('panel:registrar_usuario')

    usuarios = (
        Usuario.objects
        .filter(rol__in=[
            RolUsuario.ADMIN,
            RolUsuario.VENDEDOR,
            RolUsuario.ENCOMIENDAS,
            RolUsuario.CONDUCTOR,
        ])
        .select_related('empresa', 'trabajador_empresa')
        .order_by('-fecha_registro')
    )
    if request.user.rol != RolUsuario.SUPER_ADMIN:
        usuarios = usuarios.filter(empresa=request.user.empresa)

    return render(request, 'panel/usuarios/registrar_usuario.html', {
        'form': form,
        'usuarios': usuarios[:12],
        'roles_permisos': roles_permisos_configurados(),
    })


@permiso_panel_required('gestionar_roles')
def roles(request):
    rol_form = RolSistemaForm(prefix='rol')
    permiso_form = PermisoSistemaForm(prefix='permiso')

    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion == 'crear_rol':
            rol_form = RolSistemaForm(request.POST, prefix='rol')
            if rol_form.is_valid():
                rol_form.save()
                messages.success(request, 'Rol guardado correctamente.')
                return redirect('panel:roles')
        elif accion == 'crear_permiso':
            permiso_form = PermisoSistemaForm(request.POST, prefix='permiso')
            if permiso_form.is_valid():
                permiso_form.save()
                messages.success(request, 'Permiso guardado correctamente.')
                return redirect('panel:roles')
        elif accion == 'actualizar_rol':
            rol = get_object_or_404(RolSistema, id=request.POST.get('rol_id'))
            nombre = request.POST.get('nombre', '').strip()
            descripcion = request.POST.get('descripcion', '').strip()
            permisos_ids = request.POST.getlist('permisos')

            if nombre:
                rol.nombre = nombre
            rol.descripcion = descripcion
            rol.activo = request.POST.get('activo') == 'on'
            rol.save()

            permisos = PermisoSistema.objects.filter(id__in=permisos_ids, activo=True)
            rol.permisos.set(permisos)
            messages.success(request, f'Permisos de {rol.nombre} actualizados correctamente.')
            return redirect('panel:roles')

    roles_qs = (
        RolSistema.objects
        .filter(codigo__in=[
            RolUsuario.ADMIN,
            RolUsuario.VENDEDOR,
            RolUsuario.ENCOMIENDAS,
            RolUsuario.CONDUCTOR,
        ])
        .prefetch_related('permisos')
        .order_by('nombre')
    )
    permisos_activos = PermisoSistema.objects.filter(activo=True).order_by('modulo', 'nombre')

    return render(request, 'panel/usuarios/roles.html', {
        'rol_form': rol_form,
        'permiso_form': permiso_form,
        'roles': roles_qs,
        'roles_configurados': [
            {
                'rol': rol,
                'permisos_ids': list(rol.permisos.values_list('id', flat=True)),
            }
            for rol in roles_qs
        ],
        'permisos': PermisoSistema.objects.order_by('modulo', 'nombre'),
        'permisos_activos': permisos_activos,
        'puede_crear_rol': bool(rol_form.fields['codigo'].choices),
    })


@permiso_panel_required('gestionar_roles')
def editar_rol(request, rol_id):
    rol = get_object_or_404(RolSistema, id=rol_id)
    form = RolSistemaForm(request.POST or None, instance=rol)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Rol actualizado correctamente.')
        return redirect('panel:roles')
    return render(request, 'panel/usuarios/editar_rol.html', {'form': form, 'rol': rol})


@permiso_panel_required('gestionar_roles')
def cambiar_estado_rol(request, rol_id):
    rol = get_object_or_404(RolSistema, id=rol_id)
    rol.activo = not rol.activo
    rol.save(update_fields=['activo', 'actualizado_en'])
    messages.success(request, f'Rol {rol.nombre} {"activado" if rol.activo else "desactivado"}.')
    return redirect('panel:roles')


@permiso_panel_required('gestionar_roles')
def editar_permiso(request, permiso_id):
    permiso = get_object_or_404(PermisoSistema, id=permiso_id)
    form = PermisoSistemaForm(request.POST or None, instance=permiso)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Permiso actualizado correctamente.')
        return redirect('panel:roles')
    return render(request, 'panel/usuarios/editar_permiso.html', {'form': form, 'permiso': permiso})


@permiso_panel_required('gestionar_roles')
def cambiar_estado_permiso(request, permiso_id):
    permiso = get_object_or_404(PermisoSistema, id=permiso_id)
    permiso.activo = not permiso.activo
    permiso.save(update_fields=['activo', 'actualizado_en'])
    messages.success(request, f'Permiso {permiso.nombre} {"activado" if permiso.activo else "desactivado"}.')
    return redirect('panel:roles')


@permiso_panel_required('gestionar_trabajadores')
def trabajadores(request):
    form = FormularioTrabajadorEmpresa(request.POST or None, creado_por=request.user)

    if request.method == 'POST' and form.is_valid():
        trabajador = form.save()
        messages.success(
            request,
            f'Trabajador {trabajador.nombre_completo} registrado como {trabajador.get_cargo_display()}.',
        )
        return redirect('panel:trabajadores')

    trabajadores_qs = TrabajadorEmpresa.objects.select_related('empresa', 'usuario').order_by('-creado_en')
    if request.user.rol != RolUsuario.SUPER_ADMIN:
        trabajadores_qs = trabajadores_qs.filter(empresa=request.user.empresa)

    return render(request, 'panel/usuarios/trabajadores.html', {
        'form': form,
        'trabajadores': trabajadores_qs[:150],
    })


@panel_required
def seleccionar_asientos(request, viaje_id):
    try:
        viaje = Viaje.objects.select_related('ruta', 'bus', 'bus__empresa').get(id=viaje_id)
    except Viaje.DoesNotExist:
        return redirect('panel:dashboard')

    ocupados = list(
        Boleto.objects
        .filter(viaje=viaje)
        .exclude(estado='cancelado')
        .values_list('numero_asiento', flat=True)
    )

    cap        = viaje.bus.capacidad
    piso_split = PISO_SPLITS.get(viaje.bus.tipo_servicio, cap // 2)

    return render(request, 'panel/viajes/seleccionar_asientos.html', {
        'viaje':      viaje,
        'ocupados':   ocupados,
        'piso_split': piso_split,
    })
