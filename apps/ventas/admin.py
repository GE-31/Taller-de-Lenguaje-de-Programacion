from django.contrib import admin
from .models import Boleto, CancelacionBoleto, PagoQR, ReprogramacionBoleto


@admin.register(Boleto)
class BoletoAdmin(admin.ModelAdmin):
    list_display  = ('codigo_boleto', 'pasajero', 'viaje', 'numero_asiento', 'estado', 'precio_pagado')
    list_filter   = ('estado',)
    search_fields = ('codigo_boleto', 'pasajero__email', 'pasajero__dni')
    readonly_fields = ('codigo_boleto', 'fecha_compra')


@admin.register(PagoQR)
class PagoQRAdmin(admin.ModelAdmin):
    list_display = ('numero_operacion', 'viaje', 'monto', 'estado', 'creado_en', 'expira_en', 'pagado_en')
    list_filter = ('estado', 'creado_en', 'pagado_en')
    search_fields = ('numero_operacion', 'codigo', 'asientos_str')
    readonly_fields = ('codigo', 'numero_operacion', 'creado_en', 'pagado_en')


@admin.register(CancelacionBoleto)
class CancelacionBoletoAdmin(admin.ModelAdmin):
    list_display = ('boleto', 'pasajero_nombre', 'estado', 'monto_devuelto', 'fecha_solicitud', 'usuario')
    list_filter = ('estado', 'fecha_solicitud')
    search_fields = ('boleto__codigo_boleto', 'pasajero_nombre', 'motivo')


@admin.register(ReprogramacionBoleto)
class ReprogramacionBoletoAdmin(admin.ModelAdmin):
    list_display = ('boleto', 'viaje_anterior', 'viaje_nuevo', 'asiento_anterior', 'asiento_nuevo', 'creado_en', 'usuario')
    list_filter = ('creado_en',)
    search_fields = ('boleto__codigo_boleto', 'motivo')
