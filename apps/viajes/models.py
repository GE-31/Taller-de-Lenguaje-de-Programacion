from django.db import models
from django.utils import timezone


class EstadoViaje(models.TextChoices):
    PROGRAMADO  = 'programado', 'Programado'
    EN_EMBARQUE = 'en_embarque', 'En embarque'
    EN_CAMINO   = 'en_camino', 'En camino'
    FINALIZADO  = 'finalizado', 'Finalizado'
    CANCELADO   = 'cancelado', 'Cancelado'
    EN_CURSO    = 'en_curso', 'En curso'
    COMPLETADO  = 'completado', 'Completado'


class Viaje(models.Model):
    ruta                   = models.ForeignKey(
                                 'rutas.Ruta',
                                 on_delete=models.PROTECT,
                                 related_name='viajes',
                             )
    bus                    = models.ForeignKey(
                                 'flota.Bus',
                                 on_delete=models.PROTECT,
                                 related_name='viajes',
                             )
    fecha_salida           = models.DateTimeField()
    fecha_llegada_estimada = models.DateTimeField()
    precio                 = models.DecimalField(
                                 max_digits=8, decimal_places=2,
                                 help_text='Puede diferir del precio base de la ruta',
                             )
    estado                 = models.CharField(
                                 max_length=20,
                                 choices=EstadoViaje.choices,
                                 default=EstadoViaje.PROGRAMADO,
                             )
    creado_en              = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Viaje'
        verbose_name_plural = 'Viajes'
        ordering            = ['fecha_salida']

    def __str__(self):
        return f'{self.ruta} | {self.fecha_salida:%d/%m/%Y %H:%M} | {self.get_estado_display()}'

    def calcular_estado_operativo(self, ahora=None):
        ahora = ahora or timezone.now()
        if self.estado == EstadoViaje.CANCELADO:
            return EstadoViaje.CANCELADO

        llegada = self.fecha_llegada_estimada
        while llegada <= self.fecha_salida:
            llegada = llegada + timezone.timedelta(days=1)

        if ahora >= llegada:
            return EstadoViaje.FINALIZADO
        if ahora >= self.fecha_salida:
            return EstadoViaje.EN_CAMINO
        if self.fecha_salida - timezone.timedelta(hours=1) <= ahora < self.fecha_salida:
            return EstadoViaje.EN_EMBARQUE
        return EstadoViaje.PROGRAMADO

    @property
    def estado_operativo(self):
        return self.calcular_estado_operativo()

    @property
    def estado_operativo_display(self):
        return dict(EstadoViaje.choices).get(self.estado_operativo, self.estado_operativo)

    @property
    def asientos_disponibles(self):
        ocupados = self.boletos.exclude(estado__in=['cancelado', 'anulado', 'reprogramado']).count()
        return self.bus.capacidad - ocupados
