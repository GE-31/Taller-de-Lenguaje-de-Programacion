from django.db import migrations
from datetime import date, datetime, timedelta
from decimal import Decimal


HORARIOS_ECONOMICO = [(9, 0), (13, 0), (17, 0), (21, 0)]
HORARIOS_BUS_CAMA  = [(20, 0)]

DIAS = 60


def obtener_bus(apps, tipo_servicio, placa, capacidad):
    Empresa = apps.get_model('flota', 'Empresa')
    Bus = apps.get_model('flota', 'Bus')

    bus = Bus.objects.filter(tipo_servicio=tipo_servicio, activo=True).order_by('id').first()
    if bus:
        return bus

    empresa, _ = Empresa.objects.get_or_create(
        ruc='20123456789',
        defaults={
            'nombre': 'Linea Imperial',
            'direccion': 'Av. Bolognesi 638, Chiclayo',
            'telefono': '967271498',
            'email': 'info@lineaimperial.com.pe',
            'activo': True,
        },
    )
    bus, _ = Bus.objects.get_or_create(
        placa=placa,
        defaults={
            'empresa': empresa,
            'capacidad': capacidad,
            'tipo_servicio': tipo_servicio,
            'marca': 'Mercedes',
            'modelo': '',
            'activo': True,
        },
    )
    return bus


def forward(apps, schema_editor):
    Promocion = apps.get_model('promociones', 'Promocion')
    Ruta      = apps.get_model('rutas', 'Ruta')
    Viaje     = apps.get_model('viajes', 'Viaje')

    # ── 1. Corregir tilde en Jaén ──────────────────────────────────────
    Promocion.objects.filter(origen='Chiclayo', destino='Jaen').update(destino='Jaén')

    # ── 2. Buses de referencia ─────────────────────────────────────────
    bus_eco = obtener_bus(apps, 'economico', 'PROMO-ECO', 56)
    bus_cama = obtener_bus(apps, 'bus_cama', 'PROMO-CAMA', 48)

    hoy = date.today()

    # ── 3. Ruta Lima → Arequipa ────────────────────────────────────────
    ruta_arequipa, _ = Ruta.objects.get_or_create(
        origen='Lima', destino='Arequipa',
        defaults={
            'distancia_km': Decimal('1010.00'),
            'duracion_estimada': timedelta(hours=18),
            'precio_base': Decimal('100.00'),
            'activo': True,
        },
    )
    for delta in range(DIAS):
        d = hoy + timedelta(days=delta)
        for h, m in HORARIOS_BUS_CAMA:
            salida   = datetime(d.year, d.month, d.day, h, m)
            llegada  = salida + timedelta(hours=18)
            Viaje.objects.get_or_create(
                ruta=ruta_arequipa, bus=bus_cama,
                fecha_salida=salida,
                defaults={
                    'fecha_llegada_estimada': llegada,
                    'precio': Decimal('120.00'),
                    'estado': 'programado',
                },
            )

    # ── 4. Ruta Chiclayo → Trujillo ────────────────────────────────────
    ruta_trujillo, _ = Ruta.objects.get_or_create(
        origen='Chiclayo', destino='Trujillo',
        defaults={
            'distancia_km': Decimal('210.00'),
            'duracion_estimada': timedelta(hours=3),
            'precio_base': Decimal('30.00'),
            'activo': True,
        },
    )
    for delta in range(DIAS):
        d = hoy + timedelta(days=delta)
        for h, m in HORARIOS_ECONOMICO:
            salida  = datetime(d.year, d.month, d.day, h, m)
            llegada = salida + timedelta(hours=3)
            Viaje.objects.get_or_create(
                ruta=ruta_trujillo, bus=bus_eco,
                fecha_salida=salida,
                defaults={
                    'fecha_llegada_estimada': llegada,
                    'precio': Decimal('40.00'),
                    'estado': 'programado',
                },
            )


def backward(apps, schema_editor):
    Promocion = apps.get_model('promociones', 'Promocion')
    Ruta      = apps.get_model('rutas', 'Ruta')
    Viaje     = apps.get_model('viajes', 'Viaje')

    Promocion.objects.filter(origen='Chiclayo', destino='Jaén').update(destino='Jaen')

    for origen, destino in [('Lima', 'Arequipa'), ('Chiclayo', 'Trujillo')]:
        ruta = Ruta.objects.filter(origen=origen, destino=destino).first()
        if ruta:
            Viaje.objects.filter(ruta=ruta).delete()
            ruta.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('promociones', '0003_reseed_promociones'),
        ('rutas',  '0001_initial'),
        ('viajes', '0001_initial'),
        ('flota',  '0002_update_tipo_servicio'),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
