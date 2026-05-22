from django.db import migrations


def seed_permisos_recomendados(apps, schema_editor):
    RolSistema = apps.get_model('panel', 'RolSistema')
    PermisoSistema = apps.get_model('panel', 'PermisoSistema')

    permisos = [
        ('Ver Dashboard', 'ver_dashboard', 'Dashboard', 'Permite consultar el panel principal.'),
        ('Registrar usuarios', 'registrar_usuarios', 'Usuarios', 'Permite crear acceso al sistema para trabajadores.'),
        ('Gestionar trabajadores', 'gestionar_trabajadores', 'Trabajadores', 'Permite registrar y administrar personal de la empresa.'),
        ('Gestionar viajes', 'gestionar_viajes', 'Viajes', 'Permite administrar viajes programados.'),
        ('Gestionar boletos', 'gestionar_boletos', 'Boletos', 'Permite consultar y administrar boletos.'),
        ('Gestionar encomiendas', 'gestionar_encomiendas', 'Encomiendas', 'Permite administrar encomiendas.'),
        ('Gestionar rutas', 'gestionar_rutas', 'Rutas', 'Permite administrar rutas.'),
        ('Gestionar buses', 'gestionar_buses', 'Buses', 'Permite administrar buses.'),
        ('Gestionar promociones', 'gestionar_promociones', 'Promociones', 'Permite administrar promociones.'),
        ('Ver reportes', 'ver_reportes', 'Reportes', 'Permite consultar reportes del sistema.'),
        ('Ver viajes disponibles', 'ver_viajes_disponibles', 'Ventas', 'Permite consultar viajes disponibles para venta.'),
        ('Vender boletos', 'vender_boletos', 'Ventas', 'Permite vender boletos.'),
        ('Registrar pasajeros', 'registrar_pasajeros', 'Ventas', 'Permite registrar datos de pasajeros.'),
        ('Seleccionar asientos', 'seleccionar_asientos', 'Ventas', 'Permite seleccionar asientos para venta.'),
        ('Confirmar pagos', 'confirmar_pagos', 'Ventas', 'Permite confirmar pagos.'),
        ('Generar boletos', 'generar_boletos', 'Ventas', 'Permite generar boletos.'),
        ('Consultar promociones', 'consultar_promociones', 'Promociones', 'Permite consultar promociones disponibles.'),
        ('Registrar envios', 'registrar_envios', 'Encomiendas', 'Permite registrar envios.'),
        ('Registrar remitente', 'registrar_remitente', 'Encomiendas', 'Permite registrar datos del remitente.'),
        ('Registrar destinatario', 'registrar_destinatario', 'Encomiendas', 'Permite registrar datos del destinatario.'),
        ('Generar codigo de rastreo', 'generar_codigo_rastreo', 'Encomiendas', 'Permite generar codigo de rastreo.'),
        ('Actualizar estado del envio', 'actualizar_estado_envio', 'Encomiendas', 'Permite actualizar el estado de una encomienda.'),
        ('Marcar encomienda entregada', 'marcar_encomienda_entregada', 'Encomiendas', 'Permite marcar encomiendas como entregadas.'),
        ('Consultar encomiendas', 'consultar_encomiendas', 'Encomiendas', 'Permite consultar encomiendas.'),
        ('Imprimir comprobante', 'imprimir_comprobante', 'Encomiendas', 'Permite imprimir comprobantes.'),
        ('Ver viajes asignados', 'ver_viajes_asignados', 'Conductor', 'Permite ver viajes asignados al conductor.'),
        ('Ver ruta del viaje', 'ver_ruta_viaje', 'Conductor', 'Permite ver la ruta del viaje.'),
        ('Ver horario de salida', 'ver_horario_salida', 'Conductor', 'Permite ver el horario de salida.'),
        ('Ver bus asignado', 'ver_bus_asignado', 'Conductor', 'Permite ver el bus asignado.'),
        ('Ver lista basica de pasajeros', 'ver_lista_basica_pasajeros', 'Conductor', 'Permite ver una lista basica de pasajeros.'),
        ('Marcar viaje iniciado o finalizado', 'marcar_viaje_estado', 'Conductor', 'Permite marcar viaje como iniciado o finalizado.'),
    ]

    permisos_creados = {}
    for nombre, codigo, modulo, descripcion in permisos:
        permiso, _ = PermisoSistema.objects.update_or_create(
            codigo=codigo,
            defaults={
                'nombre': nombre,
                'modulo': modulo,
                'descripcion': descripcion,
                'activo': True,
            },
        )
        permisos_creados[codigo] = permiso

    permisos_por_rol = {
        'admin': [
            'ver_dashboard',
            'registrar_usuarios',
            'gestionar_trabajadores',
            'gestionar_viajes',
            'gestionar_boletos',
            'gestionar_encomiendas',
            'gestionar_rutas',
            'gestionar_buses',
            'gestionar_promociones',
            'ver_reportes',
        ],
        'vendedor': [
            'ver_viajes_disponibles',
            'vender_boletos',
            'registrar_pasajeros',
            'seleccionar_asientos',
            'confirmar_pagos',
            'generar_boletos',
            'consultar_promociones',
        ],
        'encomiendas': [
            'registrar_envios',
            'registrar_remitente',
            'registrar_destinatario',
            'generar_codigo_rastreo',
            'actualizar_estado_envio',
            'marcar_encomienda_entregada',
            'consultar_encomiendas',
            'imprimir_comprobante',
        ],
        'conductor': [
            'ver_viajes_asignados',
            'ver_ruta_viaje',
            'ver_horario_salida',
            'ver_bus_asignado',
            'ver_lista_basica_pasajeros',
            'marcar_viaje_estado',
        ],
    }

    for codigo_rol, codigos_permisos in permisos_por_rol.items():
        try:
            rol = RolSistema.objects.get(codigo=codigo_rol)
        except RolSistema.DoesNotExist:
            continue
        rol.permisos.set([
            permisos_creados[codigo_permiso]
            for codigo_permiso in codigos_permisos
            if codigo_permiso in permisos_creados
        ])


class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0004_trabajador_tiene_acceso_y_roles_visibles'),
    ]

    operations = [
        migrations.RunPython(seed_permisos_recomendados, migrations.RunPython.noop),
    ]
