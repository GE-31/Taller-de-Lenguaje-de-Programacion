from datetime import datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.flota.models import Bus, TipoServicio
from apps.rutas.models import Ruta
from apps.viajes.models import EstadoViaje, Viaje


JAEN = "Ja\u00e9n"
SEDE_PRINCIPAL = "Chiclayo"

SERVICIOS = (
    TipoServicio.ECONOMICO,
    TipoServicio.BUS_CAMA,
    TipoServicio.BUS_CAMA_VIP,
)

HORARIOS = {
    TipoServicio.ECONOMICO: time(8, 0),
    TipoServicio.BUS_CAMA: time(18, 30),
    TipoServicio.BUS_CAMA_VIP: time(21, 0),
}

RUTAS = [
    {
        "origen": "Chiclayo",
        "destino": "Trujillo",
        "distancia": "210.00",
        "duracion": timedelta(hours=4),
        "precio_base": "25.00",
        "precios": {
            TipoServicio.ECONOMICO: "25.00",
            TipoServicio.BUS_CAMA: "50.00",
            TipoServicio.BUS_CAMA_VIP: "35.00",
        },
    },
    {
        "origen": "Trujillo",
        "destino": "Chiclayo",
        "distancia": "210.00",
        "duracion": timedelta(hours=4),
        "precio_base": "25.00",
        "precios": {
            TipoServicio.ECONOMICO: "25.00",
            TipoServicio.BUS_CAMA: "30.00",
            TipoServicio.BUS_CAMA_VIP: "35.00",
        },
    },
    {
        "origen": "Chiclayo",
        "destino": "Lima",
        "distancia": "770.00",
        "duracion": timedelta(hours=13),
        "precio_base": "75.00",
        "precios": {
            TipoServicio.ECONOMICO: "75.00",
            TipoServicio.BUS_CAMA: "100.00",
            TipoServicio.BUS_CAMA_VIP: "130.00",
        },
    },
    {
        "origen": "Lima",
        "destino": "Chiclayo",
        "distancia": "770.00",
        "duracion": timedelta(hours=13),
        "precio_base": "75.00",
        "precios": {
            TipoServicio.ECONOMICO: "75.00",
            TipoServicio.BUS_CAMA: "100.00",
            TipoServicio.BUS_CAMA_VIP: "125.00",
        },
    },
    {
        "origen": "Chiclayo",
        "destino": "Cajamarca",
        "distancia": "265.00",
        "duracion": timedelta(hours=6, minutes=30),
        "precio_base": "40.00",
        "precios": {
            TipoServicio.ECONOMICO: "40.00",
            TipoServicio.BUS_CAMA: "55.00",
            TipoServicio.BUS_CAMA_VIP: "65.00",
        },
    },
    {
        "origen": "Cajamarca",
        "destino": "Chiclayo",
        "distancia": "265.00",
        "duracion": timedelta(hours=6, minutes=30),
        "precio_base": "40.00",
        "precios": {
            TipoServicio.ECONOMICO: "40.00",
            TipoServicio.BUS_CAMA: "55.00",
            TipoServicio.BUS_CAMA_VIP: "65.00",
        },
    },
    {
        "origen": "Chiclayo",
        "destino": JAEN,
        "distancia": "250.00",
        "duracion": timedelta(hours=6),
        "precio_base": "50.00",
        "precios": {
            TipoServicio.ECONOMICO: "50.00",
            TipoServicio.BUS_CAMA: "65.00",
            TipoServicio.BUS_CAMA_VIP: "70.00",
        },
    },
    {
        "origen": JAEN,
        "destino": "Chiclayo",
        "distancia": "250.00",
        "duracion": timedelta(hours=6),
        "precio_base": "50.00",
        "precios": {
            TipoServicio.ECONOMICO: "50.00",
            TipoServicio.BUS_CAMA: "65.00",
            TipoServicio.BUS_CAMA_VIP: "70.00",
        },
    },
    {
        "origen": "Chiclayo",
        "destino": "Chachapoyas",
        "distancia": "450.00",
        "duracion": timedelta(hours=10),
        "precio_base": "55.00",
        "precios": {
            TipoServicio.ECONOMICO: "55.00",
            TipoServicio.BUS_CAMA: "90.00",
            TipoServicio.BUS_CAMA_VIP: "100.00",
        },
    },
    {
        "origen": "Chachapoyas",
        "destino": "Chiclayo",
        "distancia": "450.00",
        "duracion": timedelta(hours=10),
        "precio_base": "55.00",
        "precios": {
            TipoServicio.ECONOMICO: "55.00",
            TipoServicio.BUS_CAMA: "75.00",
            TipoServicio.BUS_CAMA_VIP: "100.00",
        },
    },
]


class Command(BaseCommand):
    help = "Carga rutas y viajes con precios referenciales reales para los servicios disponibles."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dias",
            type=int,
            default=60,
            help="Cantidad de dias futuros a programar.",
        )

    def handle(self, *args, **options):
        dias = options["dias"]
        buses = {
            servicio: Bus.objects.filter(tipo_servicio=servicio, activo=True).order_by("id").first()
            for servicio in SERVICIOS
        }
        faltantes = [servicio for servicio, bus in buses.items() if not bus]
        if faltantes:
            raise CommandError(f"Faltan buses activos para estos servicios: {', '.join(faltantes)}")

        hoy = timezone.localdate()
        rutas_actualizadas = 0
        viajes_creados = 0
        viajes_actualizados = 0
        viajes_normalizados = 0

        rutas_desactivadas = Ruta.objects.exclude(origen=SEDE_PRINCIPAL).exclude(
            destino=SEDE_PRINCIPAL
        ).update(activo=False)

        for datos in RUTAS:
            ruta, _ = Ruta.objects.update_or_create(
                origen=datos["origen"],
                destino=datos["destino"],
                defaults={
                    "distancia_km": Decimal(datos["distancia"]),
                    "duracion_estimada": datos["duracion"],
                    "precio_base": Decimal(datos["precio_base"]),
                    "activo": True,
                },
            )
            rutas_actualizadas += 1

            for delta in range(dias):
                dia = hoy + timedelta(days=delta)
                for servicio in SERVICIOS:
                    hora = HORARIOS[servicio]
                    salida = timezone.make_aware(datetime.combine(dia, hora))
                    llegada = salida + datos["duracion"]
                    precio = Decimal(datos["precios"][servicio])
                    defaults = {
                        "fecha_llegada_estimada": llegada,
                        "precio": precio,
                        "estado": EstadoViaje.PROGRAMADO,
                    }
                    viaje, creado = Viaje.objects.update_or_create(
                        ruta=ruta,
                        bus=buses[servicio],
                        fecha_salida=salida,
                        defaults=defaults,
                    )
                    if creado:
                        viajes_creados += 1
                    else:
                        viajes_actualizados += 1

                    viajes_normalizados += Viaje.objects.filter(
                        ruta=ruta,
                        bus__tipo_servicio=servicio,
                        fecha_salida__date__gte=hoy,
                        estado=EstadoViaje.PROGRAMADO,
                    ).exclude(precio=precio).update(precio=precio)

        self.stdout.write(
            self.style.SUCCESS(
                f"Rutas actualizadas: {rutas_actualizadas}. "
                f"Rutas fuera de sede desactivadas: {rutas_desactivadas}. "
                f"Viajes creados: {viajes_creados}. "
                f"Viajes actualizados: {viajes_actualizados}. "
                f"Viajes normalizados: {viajes_normalizados}."
            )
        )
