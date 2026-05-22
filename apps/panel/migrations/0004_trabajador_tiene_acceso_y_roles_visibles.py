from django.db import migrations, models


def sincronizar_acceso(apps, schema_editor):
    TrabajadorEmpresa = apps.get_model('panel', 'TrabajadorEmpresa')
    for trabajador in TrabajadorEmpresa.objects.all():
        trabajador.tiene_acceso_sistema = bool(trabajador.usuario_id)
        trabajador.save(update_fields=['tiene_acceso_sistema'])


class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0003_trabajador_acceso_roles_operativos'),
    ]

    operations = [
        migrations.AddField(
            model_name='trabajadorempresa',
            name='tiene_acceso_sistema',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='rolsistema',
            name='codigo',
            field=models.CharField(
                choices=[
                    ('admin', 'Administrador'),
                    ('vendedor', 'Vendedor / Cajero'),
                    ('encomiendas', 'Encomiendas'),
                    ('conductor', 'Conductor'),
                ],
                max_length=20,
                unique=True,
            ),
        ),
        migrations.RunPython(sincronizar_acceso, migrations.RunPython.noop),
    ]
