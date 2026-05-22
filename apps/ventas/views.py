from decimal import Decimal

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from .models import Boleto


PUNTOS_REFERENCIA = {
    'chiclayo': 'TERMINAL TERRESTRE CHICLAYO\nAV. BOLOGNESI 638 - STAND LINEA IMPERIAL',
    'jaen': 'TERMINAL TERRESTRE JAEN\nAV. PAKAMUROS 1280 - ANDEN 04',
    'jaén': 'TERMINAL TERRESTRE JAEN\nAV. PAKAMUROS 1280 - ANDEN 04',
}


def _punto_terminal(ciudad):
    ciudad_normalizada = (ciudad or '').strip().lower()
    return PUNTOS_REFERENCIA.get(
        ciudad_normalizada,
        f'TERMINAL TERRESTRE {ciudad_normalizada.upper() or "PRINCIPAL"}\nDIRECCION REFERENCIAL S/N',
    )


def _numero_a_texto(numero):
    unidades = [
        'CERO', 'UNO', 'DOS', 'TRES', 'CUATRO', 'CINCO', 'SEIS', 'SIETE', 'OCHO',
        'NUEVE', 'DIEZ', 'ONCE', 'DOCE', 'TRECE', 'CATORCE', 'QUINCE',
        'DIECISEIS', 'DIECISIETE', 'DIECIOCHO', 'DIECINUEVE',
    ]
    decenas = {
        20: 'VEINTE',
        30: 'TREINTA',
        40: 'CUARENTA',
        50: 'CINCUENTA',
        60: 'SESENTA',
        70: 'SETENTA',
        80: 'OCHENTA',
        90: 'NOVENTA',
    }
    centenas = {
        100: 'CIEN',
        200: 'DOSCIENTOS',
        300: 'TRESCIENTOS',
        400: 'CUATROCIENTOS',
        500: 'QUINIENTOS',
        600: 'SEISCIENTOS',
        700: 'SETECIENTOS',
        800: 'OCHOCIENTOS',
        900: 'NOVECIENTOS',
    }

    if numero < 20:
        return unidades[numero]
    if numero < 30:
        return 'VEINTI' + unidades[numero - 20]
    if numero < 100:
        base = (numero // 10) * 10
        resto = numero % 10
        return decenas[base] if resto == 0 else f'{decenas[base]} Y {unidades[resto]}'
    if numero in centenas:
        return centenas[numero]
    if numero < 200:
        return f'CIENTO {_numero_a_texto(numero - 100)}'

    base = (numero // 100) * 100
    resto = numero % 100
    return centenas[base] if resto == 0 else f'{centenas[base]} {_numero_a_texto(resto)}'


def _importe_en_letras(monto):
    monto = Decimal(monto).quantize(Decimal('0.01'))
    entero = int(monto)
    centimos = int((monto - entero) * 100)
    return f'{_numero_a_texto(entero)} CON {centimos:02d}/100 SOLES'


def _contexto_boleta(boleto, modo_impresion=False):
    origen = boleto.viaje.ruta.origen
    destino = boleto.viaje.ruta.destino

    return {
        'boleto': boleto,
        'pasajero_completo': f'{boleto.nombre_pasajero} {boleto.apellido_pasajero}'.strip(),
        'ruta': f'{origen} -> {destino}',
        'empresa': boleto.viaje.bus.empresa,
        'bus': boleto.viaje.bus,
        'numero_comprobante': f'F001-{boleto.id:08d}',
        'agencia': 'AV. LIMA 342 FRENTE AL GRIFO NILO\nTELF. 986842096',
        'embarque': _punto_terminal(origen),
        'desembarque': _punto_terminal(destino),
        'importe_letras': _importe_en_letras(boleto.precio_pagado),
        'op_gravada': Decimal('0.00'),
        'op_exonerada': boleto.precio_pagado,
        'igv': Decimal('0.00'),
        'modo_impresion': modo_impresion,
    }


@require_http_methods(['GET'])
def detalle_boleta(request, codigo_boleto):
    """
    Muestra el detalle de la boleta/pasaje.
    GET /ventas/boleta/{codigo_boleto}/
    """
    boleto = get_object_or_404(Boleto, codigo_boleto=codigo_boleto)
    return render(request, 'ventas/boleta_detalle.html', _contexto_boleta(boleto))


@require_http_methods(['GET'])
def descargar_boleta(request, codigo_boleto):
    """
    Descarga la boleta como datos JSON.
    GET /ventas/boleta/{codigo_boleto}/descargar/
    """
    boleto = get_object_or_404(Boleto, codigo_boleto=codigo_boleto)

    return JsonResponse({
        'codigo': str(boleto.codigo_boleto),
        'comprobante': f'F001-{boleto.id:08d}',
        'pasajero': f'{boleto.nombre_pasajero} {boleto.apellido_pasajero}'.strip(),
        'dni': boleto.num_doc,
        'ruta': f'{boleto.viaje.ruta.origen} -> {boleto.viaje.ruta.destino}',
        'embarque': _punto_terminal(boleto.viaje.ruta.origen),
        'desembarque': _punto_terminal(boleto.viaje.ruta.destino),
        'salida': boleto.viaje.fecha_salida.isoformat(),
        'asiento': boleto.numero_asiento,
        'precio': str(boleto.precio_pagado),
    })


@require_http_methods(['GET'])
def imprimir_boleta(request, codigo_boleto):
    """
    Abre la boleta en modo impresion.
    GET /ventas/boleta/{codigo_boleto}/imprimir/
    """
    boleto = get_object_or_404(Boleto, codigo_boleto=codigo_boleto)
    return render(request, 'ventas/boleta_detalle.html', _contexto_boleta(boleto, modo_impresion=True))
