from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cuentas', '0007_alter_usuario_rol_solo_roles_sistema'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usuario',
            name='rol',
            field=models.CharField(
                choices=[
                    ('pasajero', 'Pasajero'),
                    ('admin', 'Administrador'),
                    ('admin_empresa', 'Administrador de empresa'),
                    ('super_admin', 'Super Admin'),
                ],
                default='pasajero',
                max_length=20,
            ),
        ),
    ]
