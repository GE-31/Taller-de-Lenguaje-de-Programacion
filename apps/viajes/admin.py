from django.contrib import admin
from .models import Viaje


@admin.register(Viaje)
class ViajeAdmin(admin.ModelAdmin):
    list_display  = ('ruta', 'bus', 'fecha_salida', 'precio', 'estado')
    list_filter   = ('estado', 'fecha_salida', 'ruta')
    search_fields = ('ruta__origen', 'ruta__destino', 'bus__placa')
    date_hierarchy = 'fecha_salida'
