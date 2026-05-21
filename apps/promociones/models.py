from django.db import models
from django.utils import timezone


class Promocion(models.Model):
    SERVICIOS = [
        ('economico', 'Económico'),
        ('bus_cama', 'Bus Cama'),
        ('bus_cama_vip', 'Bus Cama VIP'),
    ]

    titulo = models.CharField(max_length=200, blank=True)
    origen = models.CharField(max_length=100)
    destino = models.CharField(max_length=100)
    servicio = models.CharField(max_length=30, choices=SERVICIOS)
    precio_normal = models.DecimalField(max_digits=8, decimal_places=2)
    precio_promocional = models.DecimalField(max_digits=8, decimal_places=2)
    imagen = models.CharField(max_length=300, blank=True)
    activo = models.BooleanField(default=True)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Promoción'
        verbose_name_plural = 'Promociones'
        ordering = ['-creado_en']

    def __str__(self):
        return f"{self.titulo or f'{self.origen}→{self.destino}'} ({self.get_servicio_display()})"

    @property
    def descuento(self):
        return self.precio_normal - self.precio_promocional

    @property
    def porcentaje_descuento(self):
        if self.precio_normal:
            return int((self.descuento / self.precio_normal) * 100)
        return 0

    def es_valida(self):
        hoy = timezone.localdate()
        if not self.activo:
            return False
        if self.fecha_inicio and hoy < self.fecha_inicio:
            return False
        if self.fecha_fin and hoy > self.fecha_fin:
            return False
        return True

    def aplica_a_viaje(self, viaje):
        return (
            self.origen.strip().lower() == viaje.ruta.origen.strip().lower()
            and self.destino.strip().lower() == viaje.ruta.destino.strip().lower()
            and self.servicio == viaje.bus.tipo_servicio
            and self.es_valida()
        )
