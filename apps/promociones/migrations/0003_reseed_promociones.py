from django.db import migrations
from decimal import Decimal
import datetime


PROMOS = [
    {
        'titulo': 'Chiclayo → Lima',
        'origen': 'Chiclayo',
        'destino': 'Lima',
        'servicio': 'economico',
        'precio_normal': Decimal('80.00'),
        'precio_promocional': Decimal('55.00'),
        'imagen': 'img/promociones/Chiclayo → Lima.png',
        'activo': True,
        'fecha_inicio': datetime.date(2026, 5, 1),
        'fecha_fin': datetime.date(2026, 6, 30),
    },
    {
        'titulo': 'Chiclayo → Jaén',
        'origen': 'Chiclayo',
        'destino': 'Jaen',
        'servicio': 'bus_cama',
        'precio_normal': Decimal('50.00'),
        'precio_promocional': Decimal('35.00'),
        'imagen': 'img/promociones/Chiclayo → Jaen.png',
        'activo': True,
        'fecha_inicio': datetime.date(2026, 5, 1),
        'fecha_fin': datetime.date(2026, 6, 30),
    },
    {
        'titulo': 'Chiclayo → Chachapoyas',
        'origen': 'Chiclayo',
        'destino': 'Chachapoyas',
        'servicio': 'economico',
        'precio_normal': Decimal('60.00'),
        'precio_promocional': Decimal('42.00'),
        'imagen': 'img/promociones/Chiclayo → Chachapoyas.png',
        'activo': True,
        'fecha_inicio': datetime.date(2026, 5, 1),
        'fecha_fin': datetime.date(2026, 6, 30),
    },
    {
        'titulo': 'Chiclayo → Piura',
        'origen': 'Chiclayo',
        'destino': 'Piura',
        'servicio': 'bus_cama',
        'precio_normal': Decimal('70.00'),
        'precio_promocional': Decimal('50.00'),
        'imagen': 'img/promociones/Chiclayo → Piura.png',
        'activo': True,
        'fecha_inicio': datetime.date(2026, 5, 1),
        'fecha_fin': datetime.date(2026, 6, 30),
    },
    {
        'titulo': 'Chiclayo → Trujillo',
        'origen': 'Chiclayo',
        'destino': 'Trujillo',
        'servicio': 'economico',
        'precio_normal': Decimal('40.00'),
        'precio_promocional': Decimal('28.00'),
        'imagen': 'img/promociones/Chiclayo → Trujillo.png',
        'activo': True,
        'fecha_inicio': datetime.date(2026, 5, 1),
        'fecha_fin': datetime.date(2026, 6, 30),
    },
    {
        'titulo': 'Lima → Arequipa',
        'origen': 'Lima',
        'destino': 'Arequipa',
        'servicio': 'bus_cama',
        'precio_normal': Decimal('120.00'),
        'precio_promocional': Decimal('85.00'),
        'imagen': 'img/promociones/Lima → Arequipa.png',
        'activo': True,
        'fecha_inicio': datetime.date(2026, 5, 1),
        'fecha_fin': datetime.date(2026, 6, 30),
    },
]


def reseed(apps, schema_editor):
    Promocion = apps.get_model('promociones', 'Promocion')
    Promocion.objects.all().delete()
    for data in PROMOS:
        Promocion.objects.create(**data)


def unreseed(apps, schema_editor):
    Promocion = apps.get_model('promociones', 'Promocion')
    Promocion.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('promociones', '0002_seed_promociones'),
    ]

    operations = [
        migrations.RunPython(reseed, unreseed),
    ]
