from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('flota', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TrabajadorEmpresa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombres', models.CharField(max_length=120)),
                ('apellidos', models.CharField(max_length=120)),
                ('dni', models.CharField(max_length=8, unique=True, validators=[django.core.validators.RegexValidator(message='El DNI debe tener exactamente 8 digitos.', regex='^\\d{8}$')])),
                ('telefono', models.CharField(blank=True, max_length=9, validators=[django.core.validators.RegexValidator(message='El telefono debe tener exactamente 9 digitos.', regex='^\\d{9}$')])),
                ('cargo', models.CharField(choices=[('limpieza', 'Limpieza'), ('mantenimiento', 'Mantenimiento'), ('mecanico', 'Mecanico'), ('lavador', 'Lavador de buses'), ('patio', 'Personal de patio'), ('seguridad', 'Seguridad'), ('chofer', 'Chofer'), ('auxiliar', 'Auxiliar de bus')], max_length=30)),
                ('activo', models.BooleanField(default=True)),
                ('fecha_ingreso', models.DateField()),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='trabajadores', to='flota.empresa')),
            ],
            options={
                'verbose_name': 'Trabajador',
                'verbose_name_plural': 'Trabajadores',
                'ordering': ['apellidos', 'nombres'],
            },
        ),
    ]
