from django.contrib import admin
from .models import Empresa, Bus


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display  = ('nombre', 'ruc', 'telefono', 'email', 'activo')
    list_filter   = ('activo',)
    search_fields = ('nombre', 'ruc')


@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display  = ('placa', 'empresa', 'tipo_servicio', 'capacidad', 'activo')
    list_filter   = ('tipo_servicio', 'activo', 'empresa')
    search_fields = ('placa', 'marca', 'modelo')
