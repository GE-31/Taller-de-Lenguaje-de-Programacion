from datetime import timedelta

from django.db import migrations


RUTAS_ACTIVAS = {
    ('Chiclayo', 'Trujillo'): (timedelta(hours=3), '40.00', '210.00'),
    ('Trujillo', 'Chiclayo'): (timedelta(hours=3), '40.00', '210.00'),
    ('Chiclayo', 'Lima'): (timedelta(hours=14), '60.00', '770.00'),
    ('Lima', 'Chiclayo'): (timedelta(hours=14), '60.00', '770.00'),
    ('Chiclayo', 'Cajamarca'): (timedelta(hours=6), '30.00', '265.00'),
    ('Cajamarca', 'Chiclayo'): (timedelta(hours=6), '30.00', '265.00'),
    ('Chiclayo', 'Jaén'): (timedelta(hours=5), '28.00', '250.00'),
    ('Jaén', 'Chiclayo'): (timedelta(hours=5), '28.00', '250.00'),
}


def configurar_rutas(apps, schema_editor):
    Ruta = apps.get_model('rutas', 'Ruta')
    Ruta.objects.all().update(activo=False)

    for (origen, destino), (duracion, precio, distancia) in RUTAS_ACTIVAS.items():
        Ruta.objects.update_or_create(
            origen=origen,
            destino=destino,
            defaults={
                'duracion_estimada': duracion,
                'precio_base': precio,
                'distancia_km': distancia,
                'activo': True,
            },
        )


def revertir(apps, schema_editor):
    Ruta = apps.get_model('rutas', 'Ruta')
    Ruta.objects.all().update(activo=True)


class Migration(migrations.Migration):

    dependencies = [
        ('rutas', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(configurar_rutas, revertir),
    ]
