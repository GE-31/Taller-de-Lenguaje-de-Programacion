from django.core.validators import RegexValidator
from django.db import models

from apps.cuentas.models import RolUsuario


class PermisoSistema(models.Model):
    nombre = models.CharField(max_length=120)
    codigo = models.SlugField(max_length=80, unique=True)
    modulo = models.CharField(max_length=80)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Permiso del sistema'
        verbose_name_plural = 'Permisos del sistema'
        ordering = ['modulo', 'nombre']

    def __str__(self):
        return f'{self.nombre} ({self.modulo})'


class RolSistema(models.Model):
    CODIGOS_SISTEMA = (
        (RolUsuario.ADMIN, 'Administrador'),
        (RolUsuario.VENDEDOR, 'Vendedor / Cajero'),
        (RolUsuario.ENCOMIENDAS, 'Encomiendas'),
        (RolUsuario.CONDUCTOR, 'Conductor'),
    )

    nombre = models.CharField(max_length=120)
    codigo = models.CharField(max_length=20, choices=CODIGOS_SISTEMA, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    permisos = models.ManyToManyField(PermisoSistema, blank=True, related_name='roles')
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Rol del sistema'
        verbose_name_plural = 'Roles del sistema'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class CargoTrabajador(models.TextChoices):
    ADMINISTRADOR = 'administrador', 'Administrador'
    VENDEDOR = 'vendedor', 'Vendedor / Cajero'
    ENCOMIENDAS = 'encomiendas', 'Encomiendas'
    LIMPIEZA = 'limpieza', 'Limpieza'
    CONDUCTOR = 'conductor', 'Conductor'
    SEGURIDAD = 'seguridad', 'Seguridad'


class TrabajadorEmpresa(models.Model):
    usuario = models.OneToOneField(
        'cuentas.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trabajador_empresa',
    )
    nombres = models.CharField(max_length=120)
    apellidos = models.CharField(max_length=120)
    dni = models.CharField(
        max_length=8,
        unique=True,
        validators=[RegexValidator(regex=r'^\d{8}$', message='El DNI debe tener exactamente 8 digitos.')],
    )
    telefono = models.CharField(
        max_length=9,
        blank=True,
        validators=[RegexValidator(regex=r'^\d{9}$', message='El telefono debe tener exactamente 9 digitos.')],
    )
    cargo = models.CharField(max_length=30, choices=CargoTrabajador.choices)
    empresa = models.ForeignKey(
        'flota.Empresa',
        on_delete=models.CASCADE,
        related_name='trabajadores',
    )
    activo = models.BooleanField(default=True)
    tiene_acceso_sistema = models.BooleanField(default=False)
    fecha_ingreso = models.DateField()
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Trabajador'
        verbose_name_plural = 'Trabajadores'
        ordering = ['apellidos', 'nombres']

    def __str__(self):
        return f'{self.nombres} {self.apellidos} - {self.get_cargo_display()}'

    @property
    def nombre_completo(self):
        return f'{self.nombres} {self.apellidos}'
