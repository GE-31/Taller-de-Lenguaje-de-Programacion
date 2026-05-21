from django.contrib import admin

from .models import Encomienda


@admin.register(Encomienda)
class EncomiendaAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'numero_orden', 'remitente_nombres', 'destinatario_nombres', 'origen', 'destino', 'estado', 'condicion_pago', 'monto', 'creado_en')
    list_filter = ('estado', 'condicion_pago', 'origen', 'destino', 'empresa')
    search_fields = ('codigo', 'numero_orden', 'codigo_orden', 'remitente_nombres', 'remitente_dni', 'destinatario_nombres', 'destinatario_dni', 'clave_recojo')
    readonly_fields = ('codigo', 'numero_orden', 'codigo_orden', 'codigo_verificacion_pago', 'creado_en', 'actualizado_en', 'entregado_en', 'pagado_en')
