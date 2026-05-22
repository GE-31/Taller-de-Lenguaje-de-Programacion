from django.db import migrations
from decimal import Decimal
import datetime


PROMOS = [
    {
        'titulo': 'Lima → Cusco Económico',
        'origen': 'Lima',
        'destino': 'Cusco',
        'servicio': 'economico',
        'precio_normal': Decimal('80.00'),
        'precio_promocional': Decimal('55.00'),
        'imagen': 'img/promos/lima-cusco.jpg',
        'activo': True,
        'fecha_inicio': datetime.date(2026, 5, 1),
        'fecha_fin': datetime.date(2026, 6, 30),
    },
    {
        'titulo': 'Lima → Arequipa Bus Cama',
        'origen': 'Lima',
        'destino': 'Arequipa',
        'servicio': 'bus_cama',
        'precio_normal': Decimal('120.00'),
        'precio_promocional': Decimal('85.00'),
        'imagen': 'img/promos/lima-arequipa.jpg',
        'activo': True,
        'fecha_inicio': datetime.date(2026, 5, 1),
        'fecha_fin': datetime.date(2026, 6, 30),
    },
    {
        'titulo': 'Lima → Trujillo Bus Cama VIP',
        'origen': 'Lima',
        'destino': 'Trujillo',
        'servicio': 'bus_cama_vip',
        'precio_normal': Decimal('150.00'),
        'precio_promocional': Decimal('110.00'),
        'imagen': 'img/promos/lima-trujillo.jpg',
        'activo': True,
        'fecha_inicio': datetime.date(2026, 5, 1),
        'fecha_fin': datetime.date(2026, 6, 30),
    },
    {
        'titulo': 'Lima → Piura Económico',
        'origen': 'Lima',
        'destino': 'Piura',
        'servicio': 'economico',
        'precio_normal': Decimal('70.00'),
        'precio_promocional': Decimal('48.00'),
        'imagen': 'img/promos/lima-piura.jpg',
        'activo': True,
        'fecha_inicio': datetime.date(2026, 5, 1),
        'fecha_fin': datetime.date(2026, 6, 30),
    },
    {
        'titulo': 'Lima → Ica Bus Cama',
        'origen': 'Lima',
        'destino': 'Ica',
        'servicio': 'bus_cama',
        'precio_normal': Decimal('60.00'),
        'precio_promocional': Decimal('40.00'),
        'imagen': 'img/promos/lima-ica.jpg',
        'activo': True,
        'fecha_inicio': datetime.date(2026, 5, 1),
        'fecha_fin': datetime.date(2026, 6, 30),
    },
    {
        'titulo': 'Lima → Huancayo Bus Cama VIP',
        'origen': 'Lima',
        'destino': 'Huancayo',
        'servicio': 'bus_cama_vip',
        'precio_normal': Decimal('100.00'),
        'precio_promocional': Decimal('70.00'),
        'imagen': 'img/promos/lima-huancayo.jpg',
        'activo': True,
        'fecha_inicio': datetime.date(2026, 5, 1),
        'fecha_fin': datetime.date(2026, 6, 30),
    },
]


def seed_promociones(apps, schema_editor):
    Promocion = apps.get_model('promociones', 'Promocion')
    for data in PROMOS:
        Promocion.objects.get_or_create(
            origen=data['origen'],
            destino=data['destino'],
            servicio=data['servicio'],
            defaults=data,
        )


def unseed_promociones(apps, schema_editor):
    Promocion = apps.get_model('promociones', 'Promocion')
    for data in PROMOS:
        Promocion.objects.filter(
            origen=data['origen'],
            destino=data['destino'],
            servicio=data['servicio'],
        ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('promociones', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_promociones, unseed_promociones),
    ]
