from django.db import models


class TipoServicio(models.TextChoices):
    ECONOMICO    = 'economico',    'Económico'
    BUS_CAMA     = 'bus_cama',     'Bus Cama'
    BUS_CAMA_VIP = 'bus_cama_vip', 'Bus Cama VIP'


class Empresa(models.Model):
    nombre    = models.CharField(max_length=150)
    ruc       = models.CharField(max_length=11, unique=True)
    direccion = models.CharField(max_length=255)
    telefono  = models.CharField(max_length=20)
    email     = models.EmailField(unique=True)
    activo    = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Empresa'
        verbose_name_plural = 'Empresas'
        ordering            = ['nombre']

    def __str__(self):
        return self.nombre


class Bus(models.Model):
    empresa       = models.ForeignKey(
                        Empresa,
                        on_delete=models.CASCADE,
                        related_name='buses',
                    )
    placa         = models.CharField(max_length=10, unique=True)
    capacidad     = models.PositiveSmallIntegerField()
    tipo_servicio = models.CharField(
                        max_length=20,
                        choices=TipoServicio.choices,
                        default=TipoServicio.ECONOMICO,
                    )
    marca         = models.CharField(max_length=80, blank=True)
    modelo        = models.CharField(max_length=80, blank=True)
    anio          = models.PositiveSmallIntegerField(null=True, blank=True)
    activo        = models.BooleanField(default=True)

    class Meta:
        verbose_name        = 'Bus'
        verbose_name_plural = 'Buses'
        ordering            = ['empresa', 'placa']

    def __str__(self):
        return f'{self.placa} — {self.get_tipo_servicio_display()} ({self.empresa})'
