from django.contrib import admin
from .models import Ruta


@admin.register(Ruta)
class RutaAdmin(admin.ModelAdmin):
    list_display  = ('origen', 'destino', 'distancia_km', 'duracion_estimada', 'precio_base', 'activo')
    list_filter   = ('activo',)
    search_fields = ('origen', 'destino')
