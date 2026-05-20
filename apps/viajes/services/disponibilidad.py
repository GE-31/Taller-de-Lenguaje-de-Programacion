from django.db import transaction
from apps.rutas.models import variantes_ciudad
from apps.viajes.models import Viaje, EstadoViaje


def obtener_viajes_disponibles(origen: str, destino: str, fecha) -> list:
    return (
        Viaje.objects
        .filter(
            ruta__activo=True,
            ruta__origen__in=variantes_ciudad(origen),
            ruta__destino__in=variantes_ciudad(destino),
            fecha_salida__date=fecha,
            estado=EstadoViaje.PROGRAMADO,
        )
        .select_related('ruta', 'bus', 'bus__empresa')
        .order_by('fecha_salida')
    )


@transaction.atomic
def reservar_asiento(viaje_id: int, numero_asiento: int) -> bool:
    viaje = (
        Viaje.objects
        .select_for_update()
        .filter(id=viaje_id, estado=EstadoViaje.PROGRAMADO)
        .first()
    )
    if not viaje:
        return False

    asiento_ocupado = viaje.boletos.filter(
        numero_asiento=numero_asiento,
    ).exclude(estado='cancelado').exists()

    return not asiento_ocupado
