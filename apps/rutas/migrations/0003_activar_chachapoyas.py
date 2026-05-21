from datetime import timedelta

from django.db import migrations


RUTAS_CHACHAPOYAS = {
    ('Chiclayo', 'Chachapoyas'): (timedelta(hours=10), '55.00', '450.00'),
    ('Chachapoyas', 'Chiclayo'): (timedelta(hours=10), '55.00', '450.00'),
}


def activar_chachapoyas(apps, schema_editor):
    Ruta = apps.get_model('rutas', 'Ruta')
    for (origen, destino), (duracion, precio, distancia) in RUTAS_CHACHAPOYAS.items():
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


def desactivar_chachapoyas(apps, schema_editor):
    Ruta = apps.get_model('rutas', 'Ruta')
    Ruta.objects.filter(origen__in=['Chiclayo', 'Chachapoyas'], destino__in=['Chiclayo', 'Chachapoyas']).update(activo=False)


class Migration(migrations.Migration):

    dependencies = [
        ('rutas', '0002_configurar_rutas_activas_iniciales'),
    ]

    operations = [
        migrations.RunPython(activar_chachapoyas, desactivar_chachapoyas),
    ]
