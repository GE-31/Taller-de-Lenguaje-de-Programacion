from django.contrib import admin
from .models import Promocion


@admin.register(Promocion)
class PromocionAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'origen', 'destino', 'servicio', 'precio_normal', 'precio_promocional', 'porcentaje_descuento', 'activo', 'fecha_fin')
    list_filter = ('activo', 'servicio')
    search_fields = ('titulo', 'origen', 'destino')
    list_editable = ('activo',)
    ordering = ('-creado_en',)
