from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cuentas', '0008_alter_usuario_rol_label_admin_empresa'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usuario',
            name='rol',
            field=models.CharField(
                choices=[
                    ('pasajero', 'Pasajero'),
                    ('admin', 'Administrador'),
                    ('vendedor', 'Vendedor / Cajero'),
                    ('encomiendas', 'Encomiendas'),
                    ('conductor', 'Conductor'),
                    ('admin_empresa', 'Administrador de empresa'),
                    ('super_admin', 'Super Admin'),
                ],
                default='pasajero',
                max_length=20,
            ),
        ),
    ]
