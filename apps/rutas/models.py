import unicodedata

from django.db import models


CIUDADES_ACTIVAS = ('Cajamarca', 'Chiclayo', 'Trujillo', 'Lima', 'Jaén')
CIUDADES_ACTIVAS_DB = ('Cajamarca', 'Chiclayo', 'Trujillo', 'Lima', 'Jaén', 'Jaen', 'JaÃ©n')
RUTAS_INICIALES_ACTIVAS = (
    ('Chiclayo', 'Trujillo'),
    ('Trujillo', 'Chiclayo'),
    ('Chiclayo', 'Lima'),
    ('Lima', 'Chiclayo'),
    ('Chiclayo', 'Cajamarca'),
    ('Cajamarca', 'Chiclayo'),
    ('Chiclayo', 'Jaén'),
    ('Jaén', 'Chiclayo'),
)

CIUDADES_ACTIVAS = ('Cajamarca', 'Chachapoyas', 'Chiclayo', 'Trujillo', 'Lima', 'Jaén')
CIUDADES_ACTIVAS_DB = ('Cajamarca', 'Chachapoyas', 'Chiclayo', 'Trujillo', 'Lima', 'Jaén', 'Jaen', 'JaÃ©n', 'JaÃƒÂ©n')
RUTAS_INICIALES_ACTIVAS = tuple(dict.fromkeys((
    ('Chiclayo', 'Trujillo'),
    ('Trujillo', 'Chiclayo'),
    ('Chiclayo', 'Lima'),
    ('Lima', 'Chiclayo'),
    ('Chiclayo', 'Cajamarca'),
    ('Cajamarca', 'Chiclayo'),
    ('Chiclayo', 'Chachapoyas'),
    ('Chachapoyas', 'Chiclayo'),
    ('Chiclayo', 'Jaén'),
    ('Jaén', 'Chiclayo'),
)))


def normalizar_ciudad(ciudad):
    texto = (ciudad or '').strip()
    texto = texto.replace('Ã©', 'é')
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return texto.casefold()


def ciudad_activa(ciudad):
    return normalizar_ciudad(ciudad) in {normalizar_ciudad(c) for c in CIUDADES_ACTIVAS}


def ciudad_canonica(ciudad):
    normalizada = normalizar_ciudad(ciudad)
    for activa in CIUDADES_ACTIVAS:
        if normalizar_ciudad(activa) == normalizada:
            return activa
    return (ciudad or '').strip()


def variantes_ciudad(ciudad):
    canonica = ciudad_canonica(ciudad)
    if normalizar_ciudad(canonica) == 'jaen':
        return [canonica, 'Jaén', 'JaÃ©n', 'Jaen', 'JaÃƒÂ©n']
        return ['Jaén', 'Jaen', 'JaÃ©n']
    return [canonica]


class Ruta(models.Model):
    origen            = models.CharField(max_length=100)
    destino           = models.CharField(max_length=100)
    distancia_km      = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    duracion_estimada = models.DurationField(help_text='Duración estimada del viaje (hh:mm:ss)')
    precio_base       = models.DecimalField(max_digits=8, decimal_places=2)
    activo            = models.BooleanField(default=True)

    class Meta:
        verbose_name        = 'Ruta'
        verbose_name_plural = 'Rutas'
        unique_together     = ('origen', 'destino')
        ordering            = ['origen', 'destino']

    def __str__(self):
        return f'{self.origen} → {self.destino}'
