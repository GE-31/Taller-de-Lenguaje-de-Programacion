from django.db import migrations, models


def backfill_pagado_en(apps, schema_editor):
    Encomienda = apps.get_model('encomiendas', 'Encomienda')
    Encomienda.objects.filter(
        condicion_pago='pagado_origen',
        pagado_en__isnull=True,
    ).update(pagado_en=models.F('creado_en'))


class Migration(migrations.Migration):

    dependencies = [
        ('encomiendas', '0002_encomienda_condicion_pago_encomienda_metodo_pago_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_pagado_en, migrations.RunPython.noop),
    ]
