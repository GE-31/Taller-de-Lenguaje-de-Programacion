from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Pasajero, TarjetaCliente


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display  = ('email', 'nombres', 'apellidos', 'rol', 'empresa', 'is_active')
    list_filter   = ('rol', 'is_active', 'empresa')
    search_fields = ('email', 'nombres', 'apellidos', 'dni')
    ordering      = ('apellidos', 'nombres')

    fieldsets = (
        (None,            {'fields': ('email', 'password')}),
        ('Datos personales', {'fields': ('nombres', 'apellidos', 'dni', 'telefono')}),
        ('Rol y empresa', {'fields': ('rol', 'empresa')}),
        ('Permisos',      {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )


@admin.register(TarjetaCliente)
class TarjetaClienteAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'marca', 'ultimos_4', 'vencimiento', 'es_principal', 'creada_en')
    list_filter = ('marca', 'es_principal', 'creada_en')
    search_fields = ('usuario__email', 'usuario__dni', 'titular', 'ultimos_4')
    readonly_fields = ('creada_en',)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nombres', 'apellidos', 'dni', 'rol', 'password1', 'password2'),
        }),
    )


@admin.register(Pasajero)
class PasajeroAdmin(admin.ModelAdmin):
    list_display = ('dni', 'nombre_completo', 'telefono', 'correo', 'fecha_actualizacion')
    list_filter = ('genero', 'fecha_creacion', 'fecha_actualizacion')
    search_fields = ('dni', 'nombres', 'apellidos', 'correo')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')
    ordering = ('apellidos', 'nombres')

    fieldsets = (
        ('Información Personal', {
            'fields': ('dni', 'nombres', 'apellidos', 'genero', 'fecha_nacimiento')
        }),
        ('Datos de Contacto', {
            'fields': ('telefono', 'correo')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
