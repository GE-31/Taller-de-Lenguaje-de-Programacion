from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('flota', '0001_initial'),
    ]

    operations = [
        # Actualizar choices del campo tipo_servicio
        migrations.AlterField(
            model_name='bus',
            name='tipo_servicio',
            field=models.CharField(
                choices=[
                    ('economico',    'Económico'),
                    ('bus_cama',     'Bus Cama'),
                    ('bus_cama_vip', 'Bus Cama VIP'),
                ],
                default='economico',
                max_length=20,
            ),
        ),
        # Migrar datos: mapear valores antiguos → nuevos
        migrations.RunSQL(
            sql="""
                UPDATE flota_bus SET tipo_servicio = 'bus_cama'     WHERE tipo_servicio = 'ejecutivo';
                UPDATE flota_bus SET tipo_servicio = 'bus_cama_vip' WHERE tipo_servicio = 'cama';
                UPDATE flota_bus SET tipo_servicio = 'economico'    WHERE tipo_servicio = 'doble_piso';
            """,
            reverse_sql="""
                UPDATE flota_bus SET tipo_servicio = 'ejecutivo'  WHERE tipo_servicio = 'bus_cama';
                UPDATE flota_bus SET tipo_servicio = 'cama'       WHERE tipo_servicio = 'bus_cama_vip';
            """,
        ),
    ]
