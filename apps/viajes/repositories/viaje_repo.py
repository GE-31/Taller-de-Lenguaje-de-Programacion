from apps.viajes.models import Viaje, EstadoViaje


def get_viaje_by_id(viaje_id: int) -> Viaje | None:
    return (
        Viaje.objects
        .select_related('ruta', 'bus', 'bus__empresa')
        .filter(id=viaje_id)
        .first()
    )


def get_precio_minimo_por_fecha(ruta, fecha):
    viaje = (
        Viaje.objects
        .filter(
            ruta=ruta,
            fecha_salida__date=fecha,
            estado=EstadoViaje.PROGRAMADO,
        )
        .order_by('precio')
        .first()
    )
    return viaje.precio if viaje else None
