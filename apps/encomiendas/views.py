import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST

from apps.panel.views import ROLES_PANEL
from apps.rutas.models import Ruta

from .forms import EncomiendaForm, RecojoBuscarForm, RecojoCobroForm, RecojoEntregaForm
from .models import CondicionPagoEncomienda, Encomienda, EstadoEncomienda


def trabajador_required(view_func):
    @login_required(login_url='panel:login')
    def wrapper(request, *args, **kwargs):
        if request.user.rol not in ROLES_PANEL:
            return redirect('publico:inicio')
        return view_func(request, *args, **kwargs)
    return wrapper


ESTADOS_ACTUALIZABLES = (
    EstadoEncomienda.REGISTRADO,
    EstadoEncomienda.EN_TRANSITO,
    EstadoEncomienda.EN_AGENCIA_DESTINO,
)

ESTADOS_RECOJO = (
    EstadoEncomienda.EN_AGENCIA_DESTINO,
    EstadoEncomienda.ENTREGADO,
)

ORDEN_ESTADOS = {
    EstadoEncomienda.REGISTRADO: 0,
    EstadoEncomienda.EN_TRANSITO: 1,
    EstadoEncomienda.EN_AGENCIA_DESTINO: 2,
    EstadoEncomienda.ENTREGADO: 3,
}


def opciones_estado_para(encomienda):
    orden_actual = ORDEN_ESTADOS.get(encomienda.estado, 0)
    return [
        (value, label)
        for value, label in EstadoEncomienda.choices
        if value in ESTADOS_ACTUALIZABLES and ORDEN_ESTADOS.get(value, 99) >= orden_actual
    ]


def buscar_encomienda_para_recojo(dni, clave, usuario):
    qs = Encomienda.objects.select_related('empresa', 'registrado_por', 'entregado_por').filter(
        destinatario_dni=dni,
        clave_recojo=clave,
    ).exclude(estado=EstadoEncomienda.CANCELADO)
    if usuario.rol != 'super_admin' and usuario.empresa:
        qs = qs.filter(empresa=usuario.empresa)
    return qs.order_by('-creado_en').first()


@trabajador_required
def panel_encomiendas(request):
    if request.method == 'POST':
        form = EncomiendaForm(request.POST)
        if form.is_valid():
            encomienda = form.save(commit=False)
            encomienda.registrado_por = request.user
            encomienda.empresa = request.user.empresa
            encomienda.save()
            messages.success(
                request,
                (
                    f'Encomienda guardada. Nro orden: {encomienda.numero_orden} - '
                    f'Codigo orden: {encomienda.codigo_orden}.'
                ),
            )
            return redirect(f'{reverse("panel:encomiendas")}?boleta={encomienda.id}')
        messages.error(request, 'No se pudo registrar la encomienda. Revisa los campos marcados.')
    else:
        form = EncomiendaForm()

    encomiendas = Encomienda.objects.select_related('empresa', 'registrado_por')
    if request.user.rol != 'super_admin' and request.user.empresa:
        encomiendas = encomiendas.filter(empresa=request.user.empresa)

    q = request.GET.get('q', '').strip().upper()
    if q:
        encomiendas = encomiendas.filter(codigo__icontains=q)

    estado = request.GET.get('estado', '').strip()
    if estado:
        encomiendas = encomiendas.filter(estado=estado)
    encomiendas = list(encomiendas[:150])
    for encomienda in encomiendas:
        encomienda.opciones_estado_panel = opciones_estado_para(encomienda)

    boleta_reciente = None
    boleta_id = request.GET.get('boleta', '').strip()
    if boleta_id.isdigit():
        boleta_qs = Encomienda.objects.filter(id=boleta_id)
        if request.user.rol != 'super_admin' and request.user.empresa:
            boleta_qs = boleta_qs.filter(empresa=request.user.empresa)
        boleta_reciente = boleta_qs.first()

    return render(request, 'panel/encomiendas.html', {
        'form': form,
        'encomiendas': encomiendas,
        'estado_choices': [(value, label) for value, label in EstadoEncomienda.choices if value in ESTADOS_ACTUALIZABLES],
        'rutas_encomienda': list(Ruta.objects.filter(activo=True).values('origen', 'destino')),
        'q': q,
        'estado_filtro': estado,
        'boleta_reciente': boleta_reciente,
    })


@trabajador_required
def recojo_entrega(request):
    buscar_form = RecojoBuscarForm()
    cobro_form = RecojoCobroForm()
    entrega_form = RecojoEntregaForm()
    encomienda = None
    dni_validado = ''
    clave_validada = ''

    if request.method == 'POST':
        accion = request.POST.get('accion', 'buscar')
        buscar_form = RecojoBuscarForm(request.POST)
        if buscar_form.is_valid():
            dni_validado = buscar_form.cleaned_data['dni']
            clave_validada = buscar_form.cleaned_data['clave']
            encomienda = buscar_encomienda_para_recojo(dni_validado, clave_validada, request.user)
            if not encomienda:
                messages.error(request, 'No encontramos una encomienda con ese DNI y clave de recojo.')
            elif accion == 'cobrar':
                if encomienda.estado == EstadoEncomienda.ENTREGADO:
                    messages.error(request, 'Esta encomienda ya fue entregada.')
                elif encomienda.estado != EstadoEncomienda.EN_AGENCIA_DESTINO:
                    messages.error(request, 'Primero marca la encomienda como En agencia destino.')
                elif encomienda.pagado_en:
                    messages.info(request, 'Esta encomienda ya figura pagada.')
                else:
                    cobro_form = RecojoCobroForm(request.POST)
                    if cobro_form.is_valid():
                        encomienda.condicion_pago = CondicionPagoEncomienda.COBRO_DESTINO
                        encomienda.metodo_pago = cobro_form.cleaned_data['metodo_pago']
                        encomienda.pagado_en = timezone.now()
                        encomienda.save(update_fields=['condicion_pago', 'metodo_pago', 'pagado_en', 'actualizado_en'])
                        messages.success(request, 'Cobro registrado. Ya puedes entregar la encomienda.')
            elif accion == 'marcar_destino':
                if encomienda.estado == EstadoEncomienda.ENTREGADO:
                    messages.error(request, 'Esta encomienda ya fue entregada.')
                elif encomienda.estado == EstadoEncomienda.EN_AGENCIA_DESTINO:
                    messages.info(request, 'La encomienda ya esta en agencia destino.')
                elif encomienda.estado != EstadoEncomienda.EN_TRANSITO:
                    messages.error(request, 'Primero debe estar En transito antes de pasar a agencia destino.')
                else:
                    encomienda.estado = EstadoEncomienda.EN_AGENCIA_DESTINO
                    encomienda.save(update_fields=['estado', 'actualizado_en'])
                    messages.success(request, 'Encomienda marcada como En agencia destino.')
            elif accion == 'entregar':
                if encomienda.estado == EstadoEncomienda.ENTREGADO:
                    messages.error(request, 'Esta encomienda ya fue entregada.')
                elif encomienda.estado != EstadoEncomienda.EN_AGENCIA_DESTINO:
                    messages.error(request, 'Solo se puede entregar cuando esta En agencia destino.')
                elif not encomienda.pagado_en:
                    messages.error(request, 'Primero registra el cobro antes de entregar.')
                else:
                    entrega_form = RecojoEntregaForm(request.POST)
                    if entrega_form.is_valid():
                        encomienda.recogido_por_nombres = entrega_form.cleaned_data['recogido_por_nombres']
                        encomienda.recogido_por_dni = dni_validado
                        encomienda.entregado_por = request.user
                        encomienda.estado = EstadoEncomienda.ENTREGADO
                        encomienda.entregado_en = timezone.now()
                        encomienda.save(update_fields=[
                            'recogido_por_nombres',
                            'recogido_por_dni',
                            'entregado_por',
                            'estado',
                            'entregado_en',
                            'actualizado_en',
                        ])
                        messages.success(request, 'Encomienda entregada correctamente.')
                        return redirect('panel:encomienda_constancia', encomienda_id=encomienda.id)
        else:
            messages.error(request, 'Valida el DNI y la clave de 4 digitos.')

    if encomienda and not entrega_form.is_bound:
        entrega_form = RecojoEntregaForm(initial={
            'recogido_por_nombres': encomienda.destinatario_nombres,
        })

    return render(request, 'panel/encomienda_recojo.html', {
        'buscar_form': buscar_form,
        'cobro_form': cobro_form,
        'entrega_form': entrega_form,
        'encomienda': encomienda,
        'dni_validado': dni_validado,
        'clave_validada': clave_validada,
    })


@trabajador_required
def boleta_encomienda(request, encomienda_id):
    encomienda = get_object_or_404(
        Encomienda.objects.select_related('empresa', 'registrado_por'),
        id=encomienda_id,
    )
    if request.user.rol != 'super_admin' and request.user.empresa:
        if encomienda.empresa_id != request.user.empresa_id:
            return redirect('panel:encomiendas')

    return render(request, 'panel/encomienda_boleta.html', {
        'encomienda': encomienda,
        'numero_comprobante': f'E-{encomienda.id:06d}',
    })


@trabajador_required
def constancia_recojo(request, encomienda_id):
    encomienda = get_object_or_404(
        Encomienda.objects.select_related('empresa', 'registrado_por', 'entregado_por'),
        id=encomienda_id,
    )
    if request.user.rol != 'super_admin' and request.user.empresa:
        if encomienda.empresa_id != request.user.empresa_id:
            return redirect('panel:encomiendas')
    if encomienda.estado != EstadoEncomienda.ENTREGADO or not encomienda.pagado_en:
        messages.error(request, 'La constancia final solo se genera cuando la encomienda ya fue pagada y entregada.')
        return redirect('panel:recojo_entrega')

    return render(request, 'panel/encomienda_constancia.html', {
        'encomienda': encomienda,
        'numero_comprobante': f'R-{encomienda.id:06d}',
    })


@csrf_protect
def pagalo_web(request):
    encomienda = None
    orden_buscada = ''
    codigo_buscado = ''

    if request.method == 'POST':
        accion = request.POST.get('accion', 'buscar')
        orden_buscada = request.POST.get('numero_orden', '').strip().upper()
        codigo_buscado = request.POST.get('codigo_orden', '').strip()
        encomienda = Encomienda.objects.filter(
            numero_orden=orden_buscada,
            codigo_orden=codigo_buscado,
        ).select_related('empresa').first()

        if not encomienda:
            messages.error(request, 'No encontramos una orden con esos datos.')
        elif encomienda.estado == EstadoEncomienda.ENTREGADO:
            messages.error(request, 'Esta encomienda ya fue entregada.')
        elif accion == 'confirmar':
            codigo_verificacion = request.POST.get('codigo_verificacion', '').strip()
            if encomienda.pagado_en:
                messages.info(request, 'Esta orden ya figura pagada.')
            elif codigo_verificacion != encomienda.codigo_verificacion_pago:
                messages.error(request, 'Codigo de verificacion incorrecto.')
            else:
                encomienda.condicion_pago = CondicionPagoEncomienda.PAGADO_WEB
                encomienda.metodo_pago = 'yape'
                encomienda.pagado_en = timezone.now()
                encomienda.save(update_fields=['condicion_pago', 'metodo_pago', 'pagado_en', 'actualizado_en'])
                messages.success(request, 'Pago Yape simulado correctamente. Tu encomienda ya figura pagada.')

    return render(request, 'publico/pagalo_web.html', {
        'encomienda': encomienda,
        'numero_orden': orden_buscada,
        'codigo_orden': codigo_buscado,
    })


@trabajador_required
@require_POST
def cambiar_estado(request, encomienda_id):
    encomienda = get_object_or_404(Encomienda, id=encomienda_id)
    if request.user.rol != 'super_admin' and request.user.empresa:
        if encomienda.empresa_id != request.user.empresa_id:
            return redirect('panel:encomiendas')

    if encomienda.estado == EstadoEncomienda.ENTREGADO:
        messages.error(request, 'Esta encomienda ya fue entregada y no se puede modificar.')
        return redirect('panel:encomiendas')

    nuevo_estado = request.POST.get('estado', '')
    estados_validos = set(ESTADOS_ACTUALIZABLES)
    if nuevo_estado in estados_validos:
        if ORDEN_ESTADOS.get(nuevo_estado, -1) < ORDEN_ESTADOS.get(encomienda.estado, 0):
            messages.error(request, 'No se puede regresar a un estado anterior.')
            return redirect('panel:encomiendas')
        if nuevo_estado == EstadoEncomienda.ENTREGADO:
            messages.error(request, 'Para entregar debes validar DNI y clave en Recojo / Entrega.')
            return redirect('panel:recojo_entrega')
        encomienda.estado = nuevo_estado
        encomienda.save(update_fields=['estado', 'entregado_en', 'actualizado_en'])
        messages.success(request, f'Estado actualizado para {encomienda.codigo}.')
    return redirect('panel:encomiendas')


@require_GET
def api_rastrear(request, codigo):
    codigo = codigo.strip().upper()
    try:
        encomienda = Encomienda.objects.select_related('empresa').get(codigo=codigo)
    except Encomienda.DoesNotExist:
        return JsonResponse({
            'ok': False,
            'mensaje': 'No encontramos una encomienda con ese código.',
        }, status=404)

    return JsonResponse({
        'ok': True,
        'encomienda': encomienda.to_tracking_dict(),
    })


@require_GET
def api_rastrear_orden(request):
    numero_orden = request.GET.get('numero_orden', '').strip().upper()
    codigo_orden = request.GET.get('codigo_orden', '').strip()
    try:
        encomienda = Encomienda.objects.select_related('empresa').get(
            numero_orden=numero_orden,
            codigo_orden=codigo_orden,
        )
    except Encomienda.DoesNotExist:
        return JsonResponse({
            'ok': False,
            'mensaje': 'No encontramos una encomienda con ese numero y codigo de orden.',
        }, status=404)

    return JsonResponse({
        'ok': True,
        'encomienda': encomienda.to_tracking_dict(),
    })


@trabajador_required
@require_POST
def api_crear(request):
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'errores': {'json': ['JSON inválido.']}}, status=400)
    else:
        data = request.POST

    form = EncomiendaForm(data)
    if not form.is_valid():
        return JsonResponse({'ok': False, 'errores': form.errors.get_json_data()}, status=400)

    encomienda = form.save(commit=False)
    encomienda.registrado_por = request.user
    encomienda.empresa = request.user.empresa
    encomienda.save()
    return JsonResponse({
        'ok': True,
        'mensaje': 'Encomienda registrada correctamente.',
        'encomienda': encomienda.to_tracking_dict(),
    }, status=201)
