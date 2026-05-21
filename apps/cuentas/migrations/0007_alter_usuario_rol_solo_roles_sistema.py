from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cuentas', '0006_alter_usuario_rol'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usuario',
            name='rol',
            field=models.CharField(
                choices=[
                    ('pasajero', 'Pasajero'),
                    ('admin', 'Administrador'),
                    ('admin_empresa', 'Admin de Empresa'),
                    ('super_admin', 'Super Admin'),
                ],
                default='pasajero',
                max_length=20,
            ),
        ),
    ]
