import base64
import json
import re
import socket
from io import BytesIO

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods
from django.db import transaction
from django.utils import timezone
from datetime import date, timedelta
from apps.cuentas.models import Pasajero
from apps.rutas.models import CIUDADES_ACTIVAS, ciudad_activa, ciudad_canonica, variantes_ciudad, Ruta
from apps.viajes.models import Viaje, EstadoViaje
from apps.ventas.models import Boleto, EstadoBoleto, EstadoPagoQR, PagoQR
from apps.ventas.whatsapp import enviar_confirmacion_boleto
from apps.promociones.models import Promocion

AMENIDADES = {
    'economico':    ['Asientos reclinables', '2 pisos'],
    'bus_cama':     ['Asientos reclinables', 'WiFi', 'Aire acondicionado', '2 pisos'],
    'bus_cama_vip': ['Asientos tipo cama', 'WiFi', 'Aire acondicionado', 'Streaming', 'USB', 'Servicio VIP'],
}

BUS_IMAGES = [
    'img/autobus/autobus01.png',
    'img/autobus/autobus02.png',
    'img/autobus/autobus03.png',
    'img/autobus/autobus04.png',
]

PUNTOS_TERMINAL = {
    'chiclayo': 'TERMINAL TERRESTRE CHICLAYO\nAV. BOLOGNESI 638 - STAND LINEA IMPERIAL',
    'jaen': 'TERMINAL TERRESTRE JAEN\nAV. PAKAMUROS 1280 - ANDEN 04',
    'jaén': 'TERMINAL TERRESTRE JAEN\nAV. PAKAMUROS 1280 - ANDEN 04',
}


def punto_terminal(ciudad):
    ciudad_normalizada = (ciudad or '').strip().lower()
    return PUNTOS_TERMINAL.get(
        ciudad_normalizada,
        f'TERMINAL TERRESTRE {ciudad_normalizada.upper() or "PRINCIPAL"}\nDIRECCION REFERENCIAL S/N',
    )
 
# Piso #2 = asientos 1..split  |  Piso #1 = asientos split+1..cap
PISO_SPLITS = {
    'economico':    44,   # 56 asientos: Piso #2 = 1-44, Piso #1 = 45-56
    'bus_cama':     36,   # 48 asientos: Piso #2 = 1-36, Piso #1 = 37-48
    'bus_cama_vip': 20,   # 20 asientos: solo Piso #2 (1 piso)
}


def buscar(request):
    origen    = request.GET.get('origen', '').strip()
    destino   = request.GET.get('destino', '').strip()
    fecha_str = request.GET.get('fecha_ida', '')
    fecha_regreso_str = request.GET.get('fecha_regreso') or request.GET.get('fecha_vuelta') or ''
    hoy       = timezone.localdate()

    try:
        fecha_sel = date.fromisoformat(fecha_str)
        if fecha_sel < hoy:
            fecha_sel = hoy
    except ValueError:
        fecha_sel = hoy

    fecha_regreso_sel = None
    if fecha_regreso_str:
        try:
            fecha_regreso_sel = date.fromisoformat(fecha_regreso_str)
            if fecha_regreso_sel < hoy:
                fecha_regreso_sel = hoy
        except ValueError:
            fecha_regreso_sel = None

    viajes_ctx      = []
    viajes_regreso_ctx = []
    ruta_encontrada = None
    ruta_regreso = None
    promo_id_get    = request.GET.get('promo_id', '').strip()
    error_busqueda = ''

    origen_valido = ciudad_activa(origen) if origen else False
    destino_valido = ciudad_activa(destino) if destino else False

    if origen and destino:
        if ciudad_canonica(origen) == ciudad_canonica(destino):
            error_busqueda = 'El origen y destino no pueden ser iguales.'
        elif not origen_valido or not destino_valido:
            error_busqueda = 'Selecciona origen y destino dentro de las ciudades disponibles.'
        elif fecha_regreso_sel and fecha_regreso_sel < fecha_sel:
            error_busqueda = 'La fecha de regreso no puede ser anterior a la fecha de ida.'

    if origen and destino and not error_busqueda:
        origen_canonico = ciudad_canonica(origen)
        destino_canonico = ciudad_canonica(destino)
        qs = (
            Viaje.objects
            .filter(
                ruta__activo=True,
                ruta__origen__in=variantes_ciudad(origen_canonico),
                ruta__destino__in=variantes_ciudad(destino_canonico),
                fecha_salida__date=fecha_sel,
                estado=EstadoViaje.PROGRAMADO,
            )
            .select_related('ruta', 'bus', 'bus__empresa')
            .order_by('fecha_salida')
        )

        promos_activas = list(Promocion.objects.filter(activo=True))
        for idx, v in enumerate(qs):
            promo_viaje = next((p for p in promos_activas if p.aplica_a_viaje(v)), None)
            viajes_ctx.append({
                'obj':        v,
                'amenidades': AMENIDADES.get(v.bus.tipo_servicio, []),
                'promo':      promo_viaje,
                'bus_image':  BUS_IMAGES[idx % len(BUS_IMAGES)],
                'embarque':   punto_terminal(v.ruta.origen),
                'desembarque': punto_terminal(v.ruta.destino),
            })

        ruta_encontrada = Ruta.objects.filter(
            activo=True,
            origen__in=variantes_ciudad(origen_canonico),
            destino__in=variantes_ciudad(destino_canonico),
        ).first()

        if fecha_regreso_sel:
            qs_regreso = (
                Viaje.objects
                .filter(
                    ruta__activo=True,
                    ruta__origen__in=variantes_ciudad(destino_canonico),
                    ruta__destino__in=variantes_ciudad(origen_canonico),
                    fecha_salida__date=fecha_regreso_sel,
                    estado=EstadoViaje.PROGRAMADO,
                )
                .select_related('ruta', 'bus', 'bus__empresa')
                .order_by('fecha_salida')
            )
            for idx, v in enumerate(qs_regreso):
                promo_viaje = next((p for p in promos_activas if p.aplica_a_viaje(v)), None)
                viajes_regreso_ctx.append({
                    'obj':        v,
                    'amenidades': AMENIDADES.get(v.bus.tipo_servicio, []),
                    'promo':      promo_viaje,
                    'bus_image':  BUS_IMAGES[idx % len(BUS_IMAGES)],
                    'embarque':   punto_terminal(v.ruta.origen),
                    'desembarque': punto_terminal(v.ruta.destino),
                })
            ruta_regreso = Ruta.objects.filter(
                activo=True,
                origen__in=variantes_ciudad(destino_canonico),
                destino__in=variantes_ciudad(origen_canonico),
            ).first()

    pestanas = []
    for delta in range(7):
        f = hoy + timedelta(days=delta)
        precio_min = None
        if ruta_encontrada:
            v = (
                Viaje.objects
                .filter(
                    ruta=ruta_encontrada,
                    fecha_salida__date=f,
                    estado=EstadoViaje.PROGRAMADO,
                )
                .order_by('precio')
                .first()
            )
            if v:
                precio_min = v.precio
        pestanas.append({
            'fecha':      f,
            'precio_min': precio_min,
            'activa':     f == fecha_sel,
        })

    ctx = {
        'origen':         origen,
        'destino':        destino,
        'fecha_sel':      fecha_sel,
        'fecha_regreso_sel': fecha_regreso_sel,
        'viajes':         viajes_ctx,
        'viajes_regreso': viajes_regreso_ctx,
        'ruta':           ruta_encontrada,
        'ruta_regreso':   ruta_regreso,
        'pestanas':       pestanas,
        'sin_resultados': bool(origen and destino and not error_busqueda and not viajes_ctx),
        'sin_resultados_regreso': bool(fecha_regreso_sel and not error_busqueda and not viajes_regreso_ctx),
        'error_busqueda': error_busqueda,
        'hoy':            hoy,
        'ciudades_activas': CIUDADES_ACTIVAS,
        'bus_images':     BUS_IMAGES,
    }
    return render(request, 'viajes/buscar.html', ctx)


@require_GET
def asientos_json(request, viaje_id):
    viaje = get_object_or_404(Viaje, id=viaje_id)
    cap        = viaje.bus.capacidad
    tipo       = viaje.bus.tipo_servicio
    piso_split = PISO_SPLITS.get(tipo, cap // 2)

    activos    = viaje.boletos.exclude(estado=EstadoBoleto.CANCELADO)
    reservados = list(activos.filter(estado=EstadoBoleto.RESERVADO).values_list('numero_asiento', flat=True))
    ocupados   = list(activos.exclude(estado=EstadoBoleto.RESERVADO).values_list('numero_asiento', flat=True))

    return JsonResponse({
        'capacidad':  cap,
        'tipo':       tipo,
        'piso_split': piso_split,
        'reservados': reservados,
        'ocupados':   ocupados,
    })


def pagar(request, viaje_id):
    viaje = get_object_or_404(Viaje, id=viaje_id, estado=EstadoViaje.PROGRAMADO)
    asientos_str = request.GET.get('asientos', '')
    asientos = [int(a) for a in asientos_str.split(',') if a.strip().isdigit()]
    promo_id = request.GET.get('promo_id', '').strip()

    if not asientos:
        return redirect('viajes:buscar')

    promo = None
    if promo_id:
        try:
            promo = Promocion.objects.get(id=int(promo_id), activo=True)
            if not promo.aplica_a_viaje(viaje):
                promo = None
        except (Promocion.DoesNotExist, ValueError):
            promo = None

    precio_unitario = promo.precio_promocional if promo else viaje.precio
    total = precio_unitario * len(asientos)
    ctx = {
        'viaje':           viaje,
        'asientos':        asientos,
        'total':           total,
        'asientos_str':    asientos_str,
        'promo':           promo,
        'precio_unitario': precio_unitario,
        'error':           request.session.pop('pago_error', None),
    }
    return render(request, 'viajes/pagar.html', ctx)


def _asientos_desde_texto(asientos_str):
    return [int(a) for a in asientos_str.split(',') if a.strip().isdigit()]


def _generar_qr_base64(payload):
    import qrcode

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    image = qr.make_image(fill_color='black', back_color='white')

    buffer = BytesIO()
    image.save(buffer, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode('ascii')


def _json_body(request):
    try:
        return json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return None


def _obtener_ip_lan():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(('8.8.8.8', 80))
            return sock.getsockname()[0]
    except OSError:
        return '127.0.0.1'


def _url_lan(request, path):
    port = request.META.get('SERVER_PORT') or '8000'
    return f'{request.scheme}://{_obtener_ip_lan()}:{port}{path}'


@require_http_methods(['POST'])
def crear_pago_yape(request):
    datos = _json_body(request)
    if datos is None:
        return JsonResponse({'error': 'JSON invalido'}, status=400)

    viaje_id = datos.get('viaje_id')
    asientos_str = str(datos.get('asientos_str', '')).strip()
    asientos = _asientos_desde_texto(asientos_str)
    promo_id = datos.get('promo_id')

    if not asientos:
        return JsonResponse({'error': 'No hay asientos seleccionados'}, status=400)

    viaje = get_object_or_404(Viaje, id=viaje_id, estado=EstadoViaje.PROGRAMADO)

    promo = None
    if promo_id:
        try:
            promo = Promocion.objects.get(id=int(promo_id), activo=True)
            if not promo.aplica_a_viaje(viaje):
                promo = None
        except (Promocion.DoesNotExist, ValueError):
            promo = None

    ocupados = list(
        viaje.boletos
        .filter(numero_asiento__in=asientos)
        .exclude(estado=EstadoBoleto.CANCELADO)
        .values_list('numero_asiento', flat=True)
    )
    if ocupados:
        return JsonResponse(
            {'error': f'Los asientos {", ".join(str(n) for n in ocupados)} ya fueron reservados.'},
            status=409,
        )

    precio_unitario = promo.precio_promocional if promo else viaje.precio
    monto = precio_unitario * len(asientos)
    pago = PagoQR.objects.create(
        viaje=viaje,
        asientos_str=asientos_str,
        monto=monto,
        promo_aplicada=promo,
    )
    url_simulacion = _url_lan(request, reverse('pago_yape_lan', args=[pago.codigo]))
    payload = url_simulacion
    pago.qr_payload = url_simulacion
    pago.qr_imagen_base64 = _generar_qr_base64(payload)
    pago.save(update_fields=['qr_payload', 'qr_imagen_base64'])

    return JsonResponse({
        'codigo': str(pago.codigo),
        'numero_operacion': pago.numero_operacion,
        'monto': str(pago.monto),
        'estado': pago.estado,
        'qr': pago.qr_imagen_base64,
        'url_simulacion': url_simulacion,
        'url_laptop': reverse('pago_yape_lan', args=[pago.codigo]),
        'segundos_restantes': pago.segundos_restantes,
    }, status=201)


@require_GET
def estado_pago_yape(request, codigo):
    pago = get_object_or_404(PagoQR, codigo=codigo)
    pago.vencer_si_corresponde()
    return JsonResponse({
        'codigo': str(pago.codigo),
        'numero_operacion': pago.numero_operacion,
        'monto': str(pago.monto),
        'estado': pago.estado,
        'segundos_restantes': pago.segundos_restantes,
        'pagado_en': pago.pagado_en.isoformat() if pago.pagado_en else None,
    })


@require_http_methods(['GET'])
def simular_pago_yape(request, codigo):
    pago = get_object_or_404(
        PagoQR.objects.select_related('viaje', 'viaje__ruta'),
        codigo=codigo,
    )
    pago.vencer_si_corresponde()
    return render(request, 'viajes/yape_simulador.html', {'pago': pago})


@require_http_methods(['POST'])
def confirmar_pago_yape(request, codigo):
    with transaction.atomic():
        pago = get_object_or_404(PagoQR.objects.select_for_update(), codigo=codigo)
        pago.vencer_si_corresponde()
        if pago.estado == EstadoPagoQR.VENCIDO:
            return JsonResponse({'error': 'El codigo QR expiro', 'estado': pago.estado}, status=410)
        if pago.estado == EstadoPagoQR.PENDIENTE:
            pago.marcar_pagado()

    return JsonResponse({
        'codigo': str(pago.codigo),
        'numero_operacion': pago.numero_operacion,
        'monto': str(pago.monto),
        'estado': pago.estado,
        'pagado_en': pago.pagado_en.isoformat() if pago.pagado_en else None,
    })


@transaction.atomic
def confirmar(request):
    if request.method != 'POST':
        return redirect('viajes:buscar')

    viaje_id     = request.POST.get('viaje_id', '')
    asientos_str = request.POST.get('asientos_str', '')
    asientos     = [int(a) for a in asientos_str.split(',') if a.strip().isdigit()]
    promo_id     = request.POST.get('promo_id', '').strip()

    # Compras anónimas permitidas — pasajero es opcional
    pasajero = request.user if request.user.is_authenticated else None

    try:
        viaje = Viaje.objects.select_for_update().get(
            id=viaje_id, estado=EstadoViaje.PROGRAMADO
        )
    except Viaje.DoesNotExist:
        return redirect('viajes:buscar')

    promo = None
    if promo_id:
        try:
            promo = Promocion.objects.get(id=int(promo_id), activo=True)
            if not promo.aplica_a_viaje(viaje):
                promo = None
        except (Promocion.DoesNotExist, ValueError):
            promo = None

    ocupados = list(
        viaje.boletos
        .filter(numero_asiento__in=asientos)
        .exclude(estado=EstadoBoleto.CANCELADO)
        .values_list('numero_asiento', flat=True)
    )
    if ocupados:
        nums = ', '.join(str(n) for n in ocupados)
        request.session['pago_error'] = (
            f'Los asientos {nums} ya fueron reservados. Por favor regresa y elige otros.'
        )
        qs = f'/viajes/pagar/{viaje_id}/?asientos={asientos_str}'
        if promo:
            qs += f'&promo_id={promo.id}'
        return redirect(qs)

    precio_unitario = promo.precio_promocional if promo else viaje.precio
    total = precio_unitario * len(asientos)
    metodo_pago = request.POST.get('metodo_pago', 'yape').strip() or 'yape'
    if metodo_pago == 'yape':
        tipo_yape = request.POST.get('tipo_yape', 'qr').strip()
        if tipo_yape == 'codigo':
            yape_celular = request.POST.get('yape_celular', '').strip()
            yape_codigo = request.POST.get('yape_codigo', '').strip()
            if not re.fullmatch(r'\d{9}', yape_celular) or not re.fullmatch(r'\d{6}', yape_codigo):
                request.session['pago_error'] = 'Completa el celular Yape y el codigo de verificacion.'
                return redirect(f'/viajes/pagar/{viaje_id}/?asientos={asientos_str}')
        else:
            pago_qr_codigo = request.POST.get('pago_qr_codigo', '').strip()
            try:
                pago_qr = PagoQR.objects.select_for_update().get(
                    codigo=pago_qr_codigo,
                    viaje=viaje,
                )
            except (PagoQR.DoesNotExist, ValueError):
                request.session['pago_error'] = 'Debes confirmar el pago Yape antes de emitir la boleta.'
                return redirect(f'/viajes/pagar/{viaje_id}/?asientos={asientos_str}')

            pago_qr.vencer_si_corresponde()
            if pago_qr.estado != EstadoPagoQR.PAGADO:
                request.session['pago_error'] = 'El pago Yape aun no esta confirmado.'
                return redirect(f'/viajes/pagar/{viaje_id}/?asientos={asientos_str}')
            if pago_qr.asientos_str != asientos_str or pago_qr.monto != total:
                request.session['pago_error'] = 'El pago Yape no coincide con esta compra.'
                return redirect(f'/viajes/pagar/{viaje_id}/?asientos={asientos_str}')

    nombre_pasajero   = request.POST.get('nombres', '').strip()
    apellido_pasajero = request.POST.get('apellidos', '').strip()
    tipo_doc          = request.POST.get('tipo_doc', '').strip()
    num_doc           = request.POST.get('num_doc', '').strip()
    email_pasajero    = request.POST.get('email', '').strip()
    telefono_pasajero = request.POST.get('telefono', '').strip()
    genero_pasajero   = request.POST.get('genero', '').strip() or 'M'
    fecha_nacimiento_raw = request.POST.get('fecha_nacimiento', '').strip()

    tipos_doc_validos = {'DNI', 'Pasaporte', 'Carn\u00e9 de Extranjer\u00eda'}
    if tipo_doc not in tipos_doc_validos:
        request.session['pago_error'] = 'Selecciona un tipo de documento valido.'
        return redirect(f'/viajes/pagar/{viaje_id}/?asientos={asientos_str}')

    if not re.fullmatch(r'\d{8}', num_doc):
        request.session['pago_error'] = 'El numero de documento debe tener exactamente 8 digitos.'
        return redirect(f'/viajes/pagar/{viaje_id}/?asientos={asientos_str}')

    if not nombre_pasajero or not apellido_pasajero:
        request.session['pago_error'] = 'Completa nombres y apellidos del pasajero.'
        return redirect(f'/viajes/pagar/{viaje_id}/?asientos={asientos_str}')

    if genero_pasajero not in {'M', 'F', 'O'}:
        request.session['pago_error'] = 'Selecciona un genero valido.'
        return redirect(f'/viajes/pagar/{viaje_id}/?asientos={asientos_str}')

    fecha_nacimiento = None
    if fecha_nacimiento_raw:
        try:
            fecha_nacimiento = date.fromisoformat(fecha_nacimiento_raw)
        except ValueError:
            request.session['pago_error'] = 'La fecha de nacimiento no es valida.'
            return redirect(f'/viajes/pagar/{viaje_id}/?asientos={asientos_str}')

    pasajero_guardado = Pasajero.objects.filter(dni=num_doc).first()
    guardar_datos_pasajero = (
        pasajero_guardado is None or
        request.POST.get('guardar_datos_pasajero') == '1'
    )

    patron_email = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if pasajero_guardado:
        if not re.fullmatch(r'\d{9}', telefono_pasajero):
            telefono_pasajero = pasajero_guardado.telefono
        if not re.fullmatch(patron_email, email_pasajero):
            email_pasajero = pasajero_guardado.correo

    if guardar_datos_pasajero:
        datos_pasajero = {
            'nombres': nombre_pasajero,
            'apellidos': apellido_pasajero,
            'genero': genero_pasajero,
            'fecha_nacimiento': fecha_nacimiento,
        }

        if re.fullmatch(r'\d{9}', telefono_pasajero):
            datos_pasajero['telefono'] = telefono_pasajero
        elif pasajero_guardado is None:
            request.session['pago_error'] = 'El telefono debe tener exactamente 9 digitos.'
            return redirect(f'/viajes/pagar/{viaje_id}/?asientos={asientos_str}')

        if re.fullmatch(patron_email, email_pasajero):
            datos_pasajero['correo'] = email_pasajero.lower()
        elif pasajero_guardado is None:
            request.session['pago_error'] = 'Ingresa un correo electronico valido.'
            return redirect(f'/viajes/pagar/{viaje_id}/?asientos={asientos_str}')

        Pasajero.objects.update_or_create(
            dni=num_doc,
            defaults=datos_pasajero,
        )

    boletos = [
        Boleto.objects.create(
            pasajero=pasajero,
            viaje=viaje,
            numero_asiento=num,
            estado=EstadoBoleto.CONFIRMADO,
            precio_pagado=precio_unitario,
            promo_aplicada=promo,
            nombre_pasajero=nombre_pasajero,
            apellido_pasajero=apellido_pasajero,
            tipo_doc=tipo_doc,
            num_doc=num_doc,
            email_pasajero=email_pasajero,
            telefono_pasajero=telefono_pasajero,
        )
        for num in asientos
    ]

    for boleto in boletos:
        if boleto.telefono_pasajero:
            enviar_confirmacion_boleto(boleto)

    request.session[f'compra_{boletos[0].codigo_boleto}'] = [
        str(b.codigo_boleto) for b in boletos
    ]
    return redirect('viajes:confirmacion', codigo=boletos[0].codigo_boleto)


def confirmacion(request, codigo):
    boleto = get_object_or_404(Boleto, codigo_boleto=codigo)
    codigos = request.session.get(f'compra_{codigo}', [str(codigo)])
    todos = list(
        Boleto.objects
        .filter(codigo_boleto__in=codigos)
        .select_related('viaje', 'viaje__ruta', 'viaje__bus', 'viaje__bus__empresa', 'pasajero')
    )
    total = sum(b.precio_pagado for b in todos)
    return render(request, 'viajes/confirmacion.html', {
        'boleto':        boleto,
        'todos_boletos': todos,
        'total':         total,
        'agencia':       'AV. LIMA 342 FRENTE AL GRIFO NILO\nTELF. 986842096',
        'embarque':      punto_terminal(boleto.viaje.ruta.origen),
        'desembarque':   punto_terminal(boleto.viaje.ruta.destino),
    })
