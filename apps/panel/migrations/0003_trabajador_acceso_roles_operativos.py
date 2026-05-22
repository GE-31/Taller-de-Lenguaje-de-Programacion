from django.db import migrations, models
import django.db.models.deletion


def seed_roles_operativos(apps, schema_editor):
    RolSistema = apps.get_model('panel', 'RolSistema')
    PermisoSistema = apps.get_model('panel', 'PermisoSistema')

    permisos = {permiso.codigo: permiso for permiso in PermisoSistema.objects.all()}
    roles = [
        (
            'Vendedor / Cajero',
            'vendedor',
            'Gestiona ventas y consultas de boletos.',
            ['ver_dashboard', 'gestionar_boletos'],
        ),
        (
            'Encomiendas',
            'encomiendas',
            'Gestiona operaciones de encomiendas.',
            ['ver_dashboard', 'gestionar_encomiendas'],
        ),
        (
            'Conductor',
            'conductor',
            'Acceso operativo para conductor cuando la empresa lo permita.',
            ['ver_dashboard'],
        ),
    ]

    for nombre, codigo, descripcion, codigos_permisos in roles:
        rol, creado = RolSistema.objects.get_or_create(
            codigo=codigo,
            defaults={
                'nombre': nombre,
                'descripcion': descripcion,
                'activo': True,
            },
        )
        if creado:
            rol.permisos.set([
                permisos[codigo_permiso]
                for codigo_permiso in codigos_permisos
                if codigo_permiso in permisos
            ])


class Migration(migrations.Migration):

    dependencies = [
        ('cuentas', '0009_roles_operativos_panel'),
        ('panel', '0002_permiso_rol_sistema'),
    ]

    operations = [
        migrations.AddField(
            model_name='trabajadorempresa',
            name='usuario',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='trabajador_empresa',
                to='cuentas.usuario',
            ),
        ),
        migrations.AlterField(
            model_name='rolsistema',
            name='codigo',
            field=models.CharField(
                choices=[
                    ('super_admin', 'Super Admin'),
                    ('admin_empresa', 'Administrador de empresa'),
                    ('admin', 'Administrador'),
                    ('vendedor', 'Vendedor / Cajero'),
                    ('encomiendas', 'Encomiendas'),
                    ('conductor', 'Conductor'),
                ],
                max_length=20,
                unique=True,
            ),
        ),
        migrations.AlterField(
            model_name='trabajadorempresa',
            name='cargo',
            field=models.CharField(
                choices=[
                    ('administrador', 'Administrador'),
                    ('vendedor', 'Vendedor / Cajero'),
                    ('encomiendas', 'Encomiendas'),
                    ('limpieza', 'Limpieza'),
                    ('conductor', 'Conductor'),
                    ('seguridad', 'Seguridad'),
                ],
                max_length=30,
            ),
        ),
        migrations.RunPython(seed_roles_operativos, migrations.RunPython.noop),
    ]
