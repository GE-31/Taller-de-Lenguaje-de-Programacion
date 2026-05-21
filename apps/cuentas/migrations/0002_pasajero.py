# Generated migration for Pasajero model

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('cuentas', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Pasajero',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dni', models.CharField(
                    max_length=8,
                    unique=True,
                    validators=[django.core.validators.RegexValidator(
                        message='El DNI debe tener exactamente 8 dígitos',
                        regex='^\\d{8}$'
                    )]
                )),
                ('nombres', models.CharField(max_length=150)),
                ('apellidos', models.CharField(max_length=150)),
                ('genero', models.CharField(
                    blank=True,
                    choices=[('M', 'Masculino'), ('F', 'Femenino'), ('O', 'Otro')],
                    default='M',
                    max_length=1
                )),
                ('fecha_nacimiento', models.DateField(blank=True, null=True)),
                ('telefono', models.CharField(blank=True, default='', max_length=15)),
                ('correo', models.EmailField(blank=True, default='', max_length=254)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Pasajero',
                'verbose_name_plural': 'Pasajeros',
                'ordering': ['apellidos', 'nombres'],
            },
        ),
        migrations.AddIndex(
            model_name='pasajero',
            index=models.Index(fields=['dni'], name='cuentas_pasajero_dni_idx'),
        ),
    ]
