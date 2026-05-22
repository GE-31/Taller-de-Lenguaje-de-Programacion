from secrets import randbelow

from django.db import migrations


def generar_clave():
    return f'{randbelow(10000):04d}'


def backfill_clave_recojo(apps, schema_editor):
    Encomienda = apps.get_model('encomiendas', 'Encomienda')
    for encomienda in Encomienda.objects.filter(clave_recojo='').only('id'):
        encomienda.clave_recojo = generar_clave()
        encomienda.save(update_fields=['clave_recojo'])


class Migration(migrations.Migration):

    dependencies = [
        ('encomiendas', '0004_encomienda_clave_recojo_encomienda_entregado_por_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_clave_recojo, migrations.RunPython.noop),
    ]
