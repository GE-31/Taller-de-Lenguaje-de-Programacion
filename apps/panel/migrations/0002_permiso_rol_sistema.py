from django.db import migrations, models


def seed_roles_permisos(apps, schema_editor):
    RolSistema = apps.get_model('panel', 'RolSistema')
    PermisoSistema = apps.get_model('panel', 'PermisoSistema')

    permisos = [
        ('Ver Dashboard', 'ver_dashboard', 'Dashboard', 'Permite consultar el panel principal.'),
        ('Registrar usuarios', 'registrar_usuarios', 'Usuarios', 'Permite crear cuentas con acceso al panel.'),
        ('Gestionar trabajadores', 'gestionar_trabajadores', 'Trabajadores', 'Permite registrar y administrar personal sin acceso al panel.'),
        ('Gestionar roles', 'gestionar_roles', 'Roles', 'Permite crear roles y configurar permisos.'),
        ('Gestionar viajes', 'gestionar_viajes', 'Viajes', 'Permite administrar viajes programados.'),
        ('Gestionar boletos', 'gestionar_boletos', 'Boletos', 'Permite consultar y administrar boletos.'),
        ('Gestionar encomiendas', 'gestionar_encomiendas', 'Encomiendas', 'Permite administrar encomiendas.'),
        ('Gestionar rutas', 'gestionar_rutas', 'Rutas', 'Permite administrar rutas.'),
        ('Gestionar buses', 'gestionar_buses', 'Buses', 'Permite administrar buses.'),
        ('Gestionar usuarios', 'gestionar_usuarios', 'Usuarios', 'Permite administrar usuarios del sistema.'),
        ('Gestionar empresas', 'gestionar_empresas', 'Empresas', 'Permite administrar empresas.'),
        ('Ver reportes generales', 'ver_reportes_generales', 'Reportes', 'Permite ver reportes generales del sistema.'),
    ]
    permisos_creados = {}
    for nombre, codigo, modulo, descripcion in permisos:
        permiso, _ = PermisoSistema.objects.get_or_create(
            codigo=codigo,
            defaults={
                'nombre': nombre,
                'modulo': modulo,
                'descripcion': descripcion,
                'activo': True,
            },
        )
        permisos_creados[codigo] = permiso

    roles = [
        (
            'Super Admin',
            'super_admin',
            'Acceso total al sistema.',
            list(permisos_creados.keys()),
        ),
        (
            'Administrador de empresa',
            'admin_empresa',
            'Administra los recursos de su empresa asignada.',
            [
                'ver_dashboard',
                'registrar_usuarios',
                'gestionar_trabajadores',
                'gestionar_viajes',
                'gestionar_boletos',
                'gestionar_encomiendas',
                'gestionar_rutas',
                'gestionar_buses',
            ],
        ),
        (
            'Administrador',
            'admin',
            'Apoya la administracion diaria y operaciones permitidas.',
            [
                'ver_dashboard',
                'registrar_usuarios',
                'gestionar_trabajadores',
                'gestionar_viajes',
                'gestionar_boletos',
                'gestionar_encomiendas',
                'gestionar_rutas',
                'gestionar_buses',
            ],
        ),
    ]
    for nombre, codigo, descripcion, codigos_permisos in roles:
        rol, _ = RolSistema.objects.get_or_create(
            codigo=codigo,
            defaults={
                'nombre': nombre,
                'descripcion': descripcion,
                'activo': True,
            },
        )
        rol.permisos.set([permisos_creados[codigo_permiso] for codigo_permiso in codigos_permisos])


class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PermisoSistema',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=120)),
                ('codigo', models.SlugField(max_length=80, unique=True)),
                ('modulo', models.CharField(max_length=80)),
                ('descripcion', models.TextField(blank=True)),
                ('activo', models.BooleanField(default=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Permiso del sistema',
                'verbose_name_plural': 'Permisos del sistema',
                'ordering': ['modulo', 'nombre'],
            },
        ),
        migrations.CreateModel(
            name='RolSistema',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=120)),
                ('codigo', models.CharField(choices=[('super_admin', 'Super Admin'), ('admin_empresa', 'Administrador de empresa'), ('admin', 'Administrador')], max_length=20, unique=True)),
                ('descripcion', models.TextField(blank=True)),
                ('activo', models.BooleanField(default=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('permisos', models.ManyToManyField(blank=True, related_name='roles', to='panel.permisosistema')),
            ],
            options={
                'verbose_name': 'Rol del sistema',
                'verbose_name_plural': 'Roles del sistema',
                'ordering': ['nombre'],
            },
        ),
        migrations.RunPython(seed_roles_permisos, migrations.RunPython.noop),
    ]
