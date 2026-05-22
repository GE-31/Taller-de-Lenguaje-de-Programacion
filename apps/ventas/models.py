import uuid
from secrets import randbelow

from django.db import models
from django.utils import timezone

from apps.promociones.models import Promocion


class EstadoBoleto(models.TextChoices):
    CONFIRMADO = 'confirmado', 'Confirmado'
    PENDIENTE = 'pendiente', 'Pendiente'
    CANCELADO = 'cancelado', 'Cancelado'
    REPROGRAMADO = 'reprogramado', 'Reprogramado'
    ANULADO = 'anulado', 'Anulado'
    RESERVADO = 'reservado', 'Reservado'
    USADO = 'usado', 'Usado'


class MetodoPagoBoleto(models.TextChoices):
    EFECTIVO = 'efectivo', 'Efectivo'
    YAPE = 'yape', 'Yape'
    PLIN = 'plin', 'Plin'
    TARJETA = 'tarjeta', 'Tarjeta'
    TRANSFERENCIA = 'transferencia', 'Transferencia'


class EstadoPagoBoleto(models.TextChoices):
    CONFIRMADO = 'confirmado', 'Confirmado'
    PENDIENTE = 'pendiente', 'Pendiente'


class EstadoSolicitud(models.TextChoices):
    PENDIENTE = 'pendiente', 'Pendiente'
    APROBADO = 'aprobado', 'Aprobado'
    RECHAZADO = 'rechazado', 'Rechazado'


class EstadoPagoQR(models.TextChoices):
    PENDIENTE = 'pendiente', 'Pendiente'
    PAGADO = 'pagado', 'Pagado'
    VENCIDO = 'vencido', 'Vencido'


def generar_numero_operacion():
    return str(randbelow(9000000000) + 1000000000)


class PagoQR(models.Model):
    codigo = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    numero_operacion = models.CharField(max_length=10, unique=True, default=generar_numero_operacion)
    viaje = models.ForeignKey(
        'viajes.Viaje',
        on_delete=models.PROTECT,
        related_name='pagos_qr',
    )
    asientos_str = models.CharField(max_length=120)
    monto = models.DecimalField(max_digits=8, decimal_places=2)
    promo_aplicada = models.ForeignKey(
        Promocion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pagos_qr',
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoPagoQR.choices,
        default=EstadoPagoQR.PENDIENTE,
    )
    qr_payload = models.TextField(blank=True, default='')
    qr_imagen_base64 = models.TextField(blank=True, default='')
    creado_en = models.DateTimeField(auto_now_add=True)
    expira_en = models.DateTimeField()
    pagado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Pago QR'
        verbose_name_plural = 'Pagos QR'
        ordering = ['-creado_en']
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['numero_operacion']),
            models.Index(fields=['estado']),
        ]

    def __str__(self):
        return f'Pago QR {self.numero_operacion} - {self.get_estado_display()}'

    def save(self, *args, **kwargs):
        if not self.expira_en:
            self.expira_en = timezone.now() + timezone.timedelta(minutes=5)
        super().save(*args, **kwargs)

    @property
    def segundos_restantes(self):
        return max(0, int((self.expira_en - timezone.now()).total_seconds()))

    def vencer_si_corresponde(self):
        if self.estado == EstadoPagoQR.PENDIENTE and timezone.now() >= self.expira_en:
            self.estado = EstadoPagoQR.VENCIDO
            self.save(update_fields=['estado'])
        return self.estado

    def marcar_pagado(self):
        self.estado = EstadoPagoQR.PAGADO
        self.pagado_en = timezone.now()
        self.save(update_fields=['estado', 'pagado_en'])


class Boleto(models.Model):
    codigo_boleto = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    pasajero = models.ForeignKey(
        'cuentas.Usuario',
        on_delete=models.PROTECT,
        related_name='boletos',
        limit_choices_to={'rol': 'pasajero'},
        null=True,
        blank=True,
    )
    viaje = models.ForeignKey(
        'viajes.Viaje',
        on_delete=models.PROTECT,
        related_name='boletos',
    )
    numero_asiento = models.PositiveSmallIntegerField()
    estado = models.CharField(
        max_length=20,
        choices=EstadoBoleto.choices,
        default=EstadoBoleto.PENDIENTE,
    )
    precio_pagado = models.DecimalField(max_digits=8, decimal_places=2)
    promo_aplicada = models.ForeignKey(
        Promocion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='boletos',
    )
    fecha_compra = models.DateTimeField(default=timezone.now)
    tipo_doc = models.CharField(max_length=30, blank=True, default='DNI')
    num_doc = models.CharField(max_length=20, blank=True, default='')
    nombre_pasajero = models.CharField(max_length=150, blank=True, default='')
    apellido_pasajero = models.CharField(max_length=150, blank=True, default='')
    email_pasajero = models.EmailField(blank=True, default='')
    telefono_pasajero = models.CharField(max_length=15, blank=True, default='')
    metodo_pago = models.CharField(
        max_length=20,
        choices=MetodoPagoBoleto.choices,
        default=MetodoPagoBoleto.YAPE,
    )
    estado_pago = models.CharField(
        max_length=20,
        choices=EstadoPagoBoleto.choices,
        default=EstadoPagoBoleto.CONFIRMADO,
    )
    vendido_por = models.ForeignKey(
        'cuentas.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='boletos_vendidos_panel',
    )

    class Meta:
        verbose_name = 'Boleto'
        verbose_name_plural = 'Boletos'
        unique_together = ('viaje', 'numero_asiento')
        ordering = ['-fecha_compra']

    def __str__(self):
        return f'Boleto {self.codigo_boleto} - {self.pasajero} | Asiento {self.numero_asiento}'

    @property
    def pasajero_nombre_completo(self):
        nombre = f'{self.nombre_pasajero} {self.apellido_pasajero}'.strip()
        if nombre:
            return nombre
        if self.pasajero:
            return self.pasajero.nombre_completo
        return 'Pasajero sin nombre'

    @property
    def puede_cancelarse(self):
        return self.viaje.fecha_salida > timezone.now() and self.estado not in {
            EstadoBoleto.CANCELADO,
            EstadoBoleto.ANULADO,
            EstadoBoleto.REPROGRAMADO,
        }


class CancelacionBoleto(models.Model):
    boleto = models.ForeignKey(Boleto, on_delete=models.PROTECT, related_name='cancelaciones')
    pasajero_nombre = models.CharField(max_length=180)
    motivo = models.TextField()
    fecha_solicitud = models.DateTimeField(default=timezone.now)
    usuario = models.ForeignKey(
        'cuentas.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancelaciones_boletos',
    )
    estado = models.CharField(max_length=20, choices=EstadoSolicitud.choices, default=EstadoSolicitud.APROBADO)
    monto_devuelto = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    observacion = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Cancelacion de boleto'
        verbose_name_plural = 'Cancelaciones de boletos'
        ordering = ['-fecha_solicitud']

    def __str__(self):
        return f'Cancelacion {self.boleto.codigo_boleto} - {self.get_estado_display()}'


class ReprogramacionBoleto(models.Model):
    boleto = models.ForeignKey(Boleto, on_delete=models.PROTECT, related_name='reprogramaciones')
    viaje_anterior = models.ForeignKey(
        'viajes.Viaje',
        on_delete=models.PROTECT,
        related_name='boletos_reprogramados_origen',
    )
    viaje_nuevo = models.ForeignKey(
        'viajes.Viaje',
        on_delete=models.PROTECT,
        related_name='boletos_reprogramados_destino',
    )
    asiento_anterior = models.PositiveSmallIntegerField()
    asiento_nuevo = models.PositiveSmallIntegerField()
    usuario = models.ForeignKey(
        'cuentas.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reprogramaciones_boletos',
    )
    motivo = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Reprogramacion de boleto'
        verbose_name_plural = 'Reprogramaciones de boletos'
        ordering = ['-creado_en']

    def __str__(self):
        return f'Reprogramacion {self.boleto.codigo_boleto}'
