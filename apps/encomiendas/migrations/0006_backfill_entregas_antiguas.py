from django.db import migrations, models


def backfill_entregas_antiguas(apps, schema_editor):
    Encomienda = apps.get_model('encomiendas', 'Encomienda')
    qs = Encomienda.objects.filter(estado='entregado')
    qs.filter(recogido_por_nombres='').update(recogido_por_nombres=models.F('destinatario_nombres'))
    qs.filter(recogido_por_dni='').update(recogido_por_dni=models.F('destinatario_dni'))
    for encomienda in qs.filter(entregado_por__isnull=True, registrado_por__isnull=False).only('id', 'registrado_por'):
        encomienda.entregado_por_id = encomienda.registrado_por_id
        encomienda.save(update_fields=['entregado_por'])


class Migration(migrations.Migration):

    dependencies = [
        ('encomiendas', '0005_backfill_clave_recojo'),
    ]

    operations = [
        migrations.RunPython(backfill_entregas_antiguas, migrations.RunPython.noop),
    ]
