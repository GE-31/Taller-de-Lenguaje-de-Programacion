import uuid
from secrets import randbelow

from django.conf import settings
from django.db import models
from django.utils import timezone


class EstadoEncomienda(models.TextChoices):
    REGISTRADO = 'registrado', 'Registrado'
    EN_TRANSITO = 'en_transito', 'En tránsito'
    EN_AGENCIA_DESTINO = 'en_agencia_destino', 'En agencia destino'
    ENTREGADO = 'entregado', 'Entregado'
    CANCELADO = 'cancelado', 'Cancelado'


class CondicionPagoEncomienda(models.TextChoices):
    PAGADO_ORIGEN = 'pagado_origen', 'Pagado en agencia'
    PAGADO_WEB = 'pagado_web', 'Pagado en web'
    COBRO_DESTINO = 'cobro_destino', 'Paga al recoger'


class MetodoPagoEncomienda(models.TextChoices):
    EFECTIVO = 'efectivo', 'Efectivo'
    YAPE = 'yape', 'Yape'
    PLIN = 'plin', 'Plin'
    TARJETA = 'tarjeta', 'Tarjeta'
    TRANSFERENCIA = 'transferencia', 'Transferencia'


class Encomienda(models.Model):
    codigo = models.CharField(max_length=14, unique=True, editable=False)
    numero_orden = models.CharField(max_length=12, unique=True, editable=False, blank=True, default='')
    codigo_orden = models.CharField(max_length=6, editable=False, blank=True, default='')
    codigo_verificacion_pago = models.CharField(max_length=6, editable=False, blank=True, default='')
    remitente_nombres = models.CharField(max_length=150)
    remitente_dni = models.CharField(max_length=8)
    remitente_telefono = models.CharField(max_length=9)
    destinatario_nombres = models.CharField(max_length=150)
    destinatario_dni = models.CharField(max_length=8, blank=True)
    destinatario_telefono = models.CharField(max_length=9)
    clave_recojo = models.CharField(max_length=4, default='', blank=True)
    origen = models.CharField(max_length=100)
    destino = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=255)
    peso_kg = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    monto = models.DecimalField(max_digits=8, decimal_places=2)
    condicion_pago = models.CharField(
        max_length=20,
        choices=CondicionPagoEncomienda.choices,
        default=CondicionPagoEncomienda.PAGADO_ORIGEN,
    )
    metodo_pago = models.CharField(
        max_length=20,
        choices=MetodoPagoEncomienda.choices,
        default=MetodoPagoEncomienda.EFECTIVO,
        blank=True,
    )
    estado = models.CharField(
        max_length=30,
        choices=EstadoEncomienda.choices,
        default=EstadoEncomienda.REGISTRADO,
        db_index=True,
    )
    empresa = models.ForeignKey(
        'flota.Empresa',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='encomiendas',
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='encomiendas_registradas',
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    entregado_en = models.DateTimeField(null=True, blank=True)
    pagado_en = models.DateTimeField(null=True, blank=True)
    recogido_por_nombres = models.CharField(max_length=150, blank=True, default='')
    recogido_por_dni = models.CharField(max_length=8, blank=True, default='')
    entregado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='encomiendas_entregadas',
    )

    class Meta:
        verbose_name = 'Encomienda'
        verbose_name_plural = 'Encomiendas'
        ordering = ['-creado_en']
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['remitente_dni']),
        ]

    def __str__(self):
        return f'{self.codigo} - {self.origen} a {self.destino}'

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self.generar_codigo()
        if not self.numero_orden:
            self.numero_orden = self.generar_numero_orden()
        if not self.codigo_orden:
            self.codigo_orden = self.generar_codigo_orden()
        if not self.codigo_verificacion_pago:
            self.codigo_verificacion_pago = self.generar_codigo_verificacion_pago()
        if not self.clave_recojo:
            self.clave_recojo = self.generar_clave_recojo()
        if self.condicion_pago in {CondicionPagoEncomienda.PAGADO_ORIGEN, CondicionPagoEncomienda.PAGADO_WEB}:
            if not self.metodo_pago:
                self.metodo_pago = MetodoPagoEncomienda.EFECTIVO
            if not self.pagado_en:
                self.pagado_en = timezone.now()
        elif self.pagado_en:
            if not self.metodo_pago:
                self.metodo_pago = MetodoPagoEncomienda.EFECTIVO
        elif self.estado == EstadoEncomienda.ENTREGADO:
            if not self.pagado_en:
                self.pagado_en = timezone.now()
        else:
            self.metodo_pago = ''
            self.pagado_en = None
        if self.estado == EstadoEncomienda.ENTREGADO and not self.entregado_en:
            self.entregado_en = timezone.now()
        if self.estado != EstadoEncomienda.ENTREGADO:
            self.entregado_en = None
        super().save(*args, **kwargs)

    @staticmethod
    def generar_codigo():
        while True:
            codigo = f'LI{uuid.uuid4().hex[:10].upper()}'
            if not Encomienda.objects.filter(codigo=codigo).exists():
                return codigo

    @staticmethod
    def generar_numero_orden():
        while True:
            numero = f'ORD{randbelow(1000000000):09d}'
            if not Encomienda.objects.filter(numero_orden=numero).exists():
                return numero

    @staticmethod
    def generar_codigo_orden():
        return f'{randbelow(1000000):06d}'

    @staticmethod
    def generar_codigo_verificacion_pago():
        return f'{randbelow(1000000):06d}'

    @staticmethod
    def generar_clave_recojo():
        for _ in range(100):
            clave = f'{randbelow(10000):04d}'
            if not Encomienda.objects.exclude(estado=EstadoEncomienda.ENTREGADO).filter(clave_recojo=clave).exists():
                return clave
        return f'{randbelow(10000):04d}'

    def to_tracking_dict(self):
        return {
            'codigo': self.codigo,
            'numero_orden': self.numero_orden,
            'codigo_orden': self.codigo_orden,
            'estado': self.estado,
            'estado_texto': self.get_estado_display(),
            'condicion_pago': self.condicion_pago,
            'condicion_pago_texto': self.get_condicion_pago_display(),
            'metodo_pago': self.get_metodo_pago_display() if self.metodo_pago else '',
            'origen': self.origen,
            'destino': self.destino,
            'descripcion': self.descripcion,
            'monto': str(self.monto),
            'peso_kg': str(self.peso_kg),
            'remitente': self.remitente_nombres,
            'destinatario': self.destinatario_nombres,
            'clave_recojo': self.clave_recojo,
            'fecha_registro': self.creado_en.strftime('%d/%m/%Y %H:%M'),
            'fecha_actualizacion': self.actualizado_en.strftime('%d/%m/%Y %H:%M'),
            'fecha_entrega': self.entregado_en.strftime('%d/%m/%Y %H:%M') if self.entregado_en else '',
            'empresa': self.empresa.nombre if self.empresa else '',
        }
