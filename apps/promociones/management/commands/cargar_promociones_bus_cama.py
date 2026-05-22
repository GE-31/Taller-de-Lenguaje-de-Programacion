from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.promociones.models import Promocion


PROMOCIONES = [
    {
        "titulo": "Chiclayo -> Trujillo",
        "origen": "Chiclayo",
        "destino": "Trujillo",
        "servicio": "bus_cama",
        "precio_normal": Decimal("50.00"),
        "precio_promocional": Decimal("40.00"),
        "imagen": "img/promociones/Chiclayo \u2192 Trujillo.png",
    },
    {
        "titulo": "Chiclayo -> Chachapoyas",
        "origen": "Chiclayo",
        "destino": "Chachapoyas",
        "servicio": "bus_cama",
        "precio_normal": Decimal("90.00"),
        "precio_promocional": Decimal("75.00"),
        "imagen": "img/promociones/Chiclayo \u2192 Chachapoyas.png",
    },
    {
        "titulo": "Chiclayo -> Lima",
        "origen": "Chiclayo",
        "destino": "Lima",
        "servicio": "bus_cama",
        "precio_normal": Decimal("100.00"),
        "precio_promocional": Decimal("89.00"),
        "imagen": "img/promociones/Chiclayo \u2192 Lima.png",
    },
    {
        "titulo": "Chiclayo -> Jaen",
        "origen": "Chiclayo",
        "destino": "Ja\u00e9n",
        "servicio": "bus_cama",
        "precio_normal": Decimal("65.00"),
        "precio_promocional": Decimal("35.00"),
        "imagen": "img/promociones/Chiclayo \u2192 Jaen.png",
    },
]


class Command(BaseCommand):
    help = "Carga las promociones activas de Bus Cama indicadas para Chiclayo."

    @transaction.atomic
    def handle(self, *args, **options):
        pares = {(promo["origen"], promo["destino"]) for promo in PROMOCIONES}
        Promocion.objects.exclude(
            origen__in=[origen for origen, _ in pares],
            destino__in=[destino for _, destino in pares],
        ).update(activo=False)

        actualizadas = 0
        for datos in PROMOCIONES:
            existentes = Promocion.objects.filter(
                origen=datos["origen"],
                destino=datos["destino"],
            ).order_by("id")
            promo = existentes.first()
            if promo is None:
                Promocion.objects.create(**datos, activo=True)
            else:
                for campo, valor in datos.items():
                    setattr(promo, campo, valor)
                promo.activo = True
                promo.save()
                existentes.exclude(id=promo.id).update(activo=False)
            actualizadas += 1

        self.stdout.write(
            self.style.SUCCESS(f"Promociones Bus Cama actualizadas: {actualizadas}.")
        )
