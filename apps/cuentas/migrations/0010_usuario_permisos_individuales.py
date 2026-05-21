from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cuentas', '0009_roles_operativos_panel'),
        ('panel', '0005_seed_permisos_recomendados_operativos'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='permisos',
            field=models.ManyToManyField(
                blank=True,
                related_name='usuarios_directos',
                to='panel.permisosistema',
                verbose_name='Permisos individuales',
            ),
        ),
    ]
