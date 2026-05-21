from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.core.validators import RegexValidator


class RolUsuario(models.TextChoices):
    PASAJERO      = 'pasajero',       'Pasajero'
    ADMIN         = 'admin',          'Administrador'
    VENDEDOR      = 'vendedor',       'Vendedor / Cajero'
    ENCOMIENDAS   = 'encomiendas',    'Encomiendas'
    CONDUCTOR     = 'conductor',      'Conductor'
    ADMIN_EMPRESA = 'admin_empresa',  'Administrador de empresa'
    SUPER_ADMIN   = 'super_admin',    'Super Admin'


class ManagerUsuario(BaseUserManager):
    def create_user(self, email, password=None, **campos_extra):
        if not email:
            raise ValueError('El correo electrónico es obligatorio.')
        email = self.normalize_email(email)
        usuario = self.model(email=email, **campos_extra)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, email, password=None, **campos_extra):
        campos_extra.setdefault('is_staff', True)
        campos_extra.setdefault('is_superuser', True)
        campos_extra.setdefault('rol', RolUsuario.SUPER_ADMIN)
        return self.create_user(email, password, **campos_extra)


class Usuario(AbstractBaseUser, PermissionsMixin):
    email          = models.EmailField(unique=True)
    nombres        = models.CharField(max_length=100)
    apellidos      = models.CharField(max_length=100)
    dni            = models.CharField(
                         max_length=8,
                         unique=True,
                         validators=[RegexValidator(
                             regex=r'^\d{8}$',
                             message='El DNI debe tener exactamente 8 dígitos'
                         )]
                     )
    telefono       = models.CharField(
                         max_length=9,
                         blank=True,
                         validators=[RegexValidator(
                             regex=r'^\d{9}$',
                             message='El teléfono debe tener exactamente 9 dígitos'
                         )]
                     )
    rol            = models.CharField(
                         max_length=20,
                         choices=RolUsuario.choices,
                         default=RolUsuario.PASAJERO,
                     )
    empresa        = models.ForeignKey(
                         'flota.Empresa',
                         on_delete=models.SET_NULL,
                         null=True, blank=True,
                         related_name='empleados',
                     )
    permisos       = models.ManyToManyField(
                         'panel.PermisoSistema',
                         blank=True,
                         related_name='usuarios_directos',
                         verbose_name='Permisos individuales',
                     )
    is_active      = models.BooleanField(default=True)
    is_staff       = models.BooleanField(default=False)
    fecha_registro = models.DateTimeField(default=timezone.now)

    objects = ManagerUsuario()

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['nombres', 'apellidos', 'dni']

    class Meta:
        verbose_name        = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering            = ['apellidos', 'nombres']

    def __str__(self):
        return f'{self.nombres} {self.apellidos} ({self.get_rol_display()})'

    @property
    def nombre_completo(self):
        return f'{self.nombres} {self.apellidos}'


class GeneroChoices(models.TextChoices):
    MASCULINO = 'M', 'Masculino'
    FEMENINO = 'F', 'Femenino'
    OTRO = 'O', 'Otro'


class Pasajero(models.Model):
    """
    Modelo para almacenar datos de pasajeros que compran boletos.
    Se utiliza para autocompletar información en futuras compras.
    """
    dni = models.CharField(
        max_length=8,
        unique=True,
        validators=[RegexValidator(
            regex=r'^\d{8}$',
            message='El DNI debe tener exactamente 8 dígitos'
        )]
    )
    nombres = models.CharField(max_length=150)
    apellidos = models.CharField(max_length=150)
    genero = models.CharField(
        max_length=1,
        choices=GeneroChoices.choices,
        blank=True,
        default='M'
    )
    fecha_nacimiento = models.DateField(null=True, blank=True)
    telefono = models.CharField(
        max_length=9,
        blank=True,
        default='',
        validators=[RegexValidator(
            regex=r'^\d{9}$',
            message='El teléfono debe tener exactamente 9 dígitos'
        )]
    )
    correo = models.EmailField(blank=True, default='')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Pasajero'
        verbose_name_plural = 'Pasajeros'
        ordering = ['apellidos', 'nombres']
        indexes = [
            models.Index(fields=['dni']),
        ]

    def __str__(self):
        return f'{self.nombres} {self.apellidos} (DNI: {self.dni})'

    @property
    def nombre_completo(self):
        return f'{self.nombres} {self.apellidos}'

    def telefonos_parcial(self):
        """Retorna teléfono con últimos 3 dígitos visibles: 967271XXX"""
        if len(self.telefono) >= 3:
            return self.telefono[:-3] + 'XXX'
        return 'XXX' * ((len(self.telefono) + 2) // 3)

    def correo_parcial(self):
        """Retorna correo oculto: geo****@gmail.com"""
        if '@' not in self.correo:
            return ''
        local, dominio = self.correo.split('@', 1)
        if len(local) <= 3:
            return f'{"*" * len(local)}@{dominio}'
        visible = local[:3]
        ocultos = '****'
        return f'{visible}{ocultos}@{dominio}'

    def to_dict(self, incluir_completos=False):
        """Convierte pasajero a diccionario con datos opcionalmente ocultos"""
        return {
            'id': self.id,
            'dni': self.dni,
            'nombres': self.nombres,
            'apellidos': self.apellidos,
            'genero': self.genero,
            'fecha_nacimiento': self.fecha_nacimiento.isoformat() if self.fecha_nacimiento else None,
            'telefono': self.telefono if incluir_completos else self.telefonos_parcial(),
            'correo': self.correo if incluir_completos else self.correo_parcial(),
            'existe': True,
        }


class TarjetaCliente(models.Model):
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='tarjetas',
    )
    titular = models.CharField(max_length=120)
    marca = models.CharField(max_length=30)
    ultimos_4 = models.CharField(max_length=4)
    mes_expiracion = models.PositiveSmallIntegerField()
    anio_expiracion = models.PositiveSmallIntegerField()
    es_principal = models.BooleanField(default=False)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Tarjeta de cliente'
        verbose_name_plural = 'Tarjetas de clientes'
        ordering = ['-es_principal', '-creada_en']

    def __str__(self):
        return f'{self.marca} **** {self.ultimos_4} - {self.usuario.email}'

    @property
    def vencimiento(self):
        return f'{self.mes_expiracion:02d}/{self.anio_expiracion}'
