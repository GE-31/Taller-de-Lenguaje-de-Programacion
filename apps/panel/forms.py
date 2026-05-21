from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as CoreValidationError
from django.db import transaction

from apps.cuentas.models import RolUsuario, Usuario
from apps.flota.models import Empresa
from apps.panel.models import CargoTrabajador, PermisoSistema, RolSistema, TrabajadorEmpresa
from apps.rutas.models import CIUDADES_ACTIVAS_DB, Ruta
from apps.flota.models import Bus
from apps.ventas.models import Boleto, EstadoBoleto, EstadoPagoBoleto, MetodoPagoBoleto
from apps.viajes.models import EstadoViaje, Viaje


INPUT_CLASS = (
    'w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-800 '
    'outline-none transition focus:border-orange-300 focus:bg-white focus:ring-4 focus:ring-orange-100'
)

SELECT_CLASS = (
    'w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-800 '
    'outline-none transition focus:border-orange-300 focus:bg-white focus:ring-4 focus:ring-orange-100'
)

TEXTAREA_CLASS = (
    'w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-800 '
    'outline-none transition focus:border-orange-300 focus:bg-white focus:ring-4 focus:ring-orange-100'
)

ROLES_ACCESO_TRABAJADOR = (
    (RolUsuario.ADMIN, 'Administrador'),
    (RolUsuario.VENDEDOR, 'Vendedor / Cajero'),
    (RolUsuario.ENCOMIENDAS, 'Encomiendas'),
    (RolUsuario.CONDUCTOR, 'Conductor'),
)


class FormularioRegistroUsuarioSistema(forms.Form):
    trabajador = forms.ModelChoiceField(
        label='Trabajador',
        queryset=TrabajadorEmpresa.objects.none(),
        widget=forms.Select(attrs={'class': SELECT_CLASS, 'id': 'id_trabajador_acceso'}),
    )
    email = forms.EmailField(
        label='Correo electronico',
        widget=forms.EmailInput(attrs={'class': INPUT_CLASS, 'placeholder': 'correo@empresa.com'}),
    )
    password1 = forms.CharField(
        label='Contrasena',
        widget=forms.PasswordInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': 'Minimo 8 caracteres',
            'autocomplete': 'new-password',
        }),
    )
    password2 = forms.CharField(
        label='Confirmar contrasena',
        widget=forms.PasswordInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': 'Repite la contrasena',
            'autocomplete': 'new-password',
        }),
    )
    rol = forms.ChoiceField(
        label='Rol del sistema',
        choices=ROLES_ACCESO_TRABAJADOR,
        widget=forms.Select(attrs={'class': SELECT_CLASS}),
    )
    empresa = forms.ModelChoiceField(
        label='Empresa',
        queryset=Empresa.objects.none(),
        widget=forms.Select(attrs={'class': SELECT_CLASS}),
    )
    is_active = forms.BooleanField(
        label='Usuario activo',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'h-5 w-5 rounded border-slate-300 text-orange-600 focus:ring-orange-500',
        }),
    )

    def __init__(self, *args, creado_por=None, **kwargs):
        self.creado_por = creado_por
        super().__init__(*args, **kwargs)

        trabajadores = (
            TrabajadorEmpresa.objects
            .filter(usuario__isnull=True, activo=True)
            .exclude(cargo__in=[CargoTrabajador.LIMPIEZA, CargoTrabajador.SEGURIDAD])
            .select_related('empresa')
            .order_by('apellidos', 'nombres')
        )
        empresas = Empresa.objects.filter(activo=True).order_by('nombre')

        if creado_por and creado_por.rol != RolUsuario.SUPER_ADMIN:
            if creado_por and creado_por.empresa:
                trabajadores = trabajadores.filter(empresa=creado_por.empresa)
                empresas = Empresa.objects.filter(pk=creado_por.empresa_id)
                self.fields['empresa'].initial = creado_por.empresa
                self.fields['empresa'].disabled = True

        self.fields['trabajador'].queryset = trabajadores
        self.fields['empresa'].queryset = empresas

        roles_qs = RolSistema.objects.filter(
            activo=True,
            codigo__in=[codigo for codigo, _ in ROLES_ACCESO_TRABAJADOR],
        ).order_by('nombre')
        roles_db = [(rol.codigo, rol.nombre) for rol in roles_qs]
        self.fields['rol'].choices = roles_db or ROLES_ACCESO_TRABAJADOR

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError('Este correo ya esta registrado.')
        return email

    def clean(self):
        cleaned = super().clean()
        trabajador = cleaned.get('trabajador')
        rol = cleaned.get('rol')
        empresa = cleaned.get('empresa')
        password1 = cleaned.get('password1', '')
        password2 = cleaned.get('password2', '')

        roles_sistema = {
            RolUsuario.ADMIN,
            RolUsuario.VENDEDOR,
            RolUsuario.ENCOMIENDAS,
            RolUsuario.CONDUCTOR,
        }
        if rol not in roles_sistema:
            self.add_error('rol', 'Selecciona un rol valido del sistema.')

        if trabajador:
            if trabajador.usuario_id or Usuario.objects.filter(dni=trabajador.dni).exists():
                self.add_error('trabajador', 'Este trabajador ya tiene usuario relacionado.')
            if trabajador.cargo in {CargoTrabajador.LIMPIEZA, CargoTrabajador.SEGURIDAD}:
                self.add_error('trabajador', 'Limpieza y Seguridad son cargos sin acceso al sistema.')
            if empresa and trabajador.empresa_id != empresa.id:
                self.add_error('empresa', 'La empresa debe coincidir con la empresa del trabajador.')
            cleaned['empresa'] = trabajador.empresa

        if self.creado_por and self.creado_por.rol != RolUsuario.SUPER_ADMIN:
            if self.creado_por.empresa:
                cleaned['empresa'] = self.creado_por.empresa
            else:
                self.add_error('empresa', 'Tu usuario administrador no tiene una empresa asignada.')

        if rol in roles_sistema and not cleaned.get('empresa'):
            self.add_error('empresa', 'Selecciona la empresa del usuario.')

        if password1 and password2 and password1 != password2:
            self.add_error('password2', 'Las contrasenas no coinciden.')

        if password1:
            try:
                validate_password(password1)
            except CoreValidationError as error:
                self.add_error('password1', list(error.messages))

        return cleaned

    def save(self):
        trabajador = self.cleaned_data['trabajador']
        usuario = Usuario(
            email=self.cleaned_data['email'],
            nombres=trabajador.nombres,
            apellidos=trabajador.apellidos,
            dni=trabajador.dni,
            telefono=trabajador.telefono,
            rol=self.cleaned_data['rol'],
            empresa=trabajador.empresa,
            is_active=self.cleaned_data.get('is_active', True),
            is_staff=True,
            is_superuser=False,
        )
        usuario.set_password(self.cleaned_data['password1'])
        with transaction.atomic():
            usuario.save()
            trabajador.usuario = usuario
            trabajador.tiene_acceso_sistema = True
            trabajador.save(update_fields=['usuario', 'tiene_acceso_sistema', 'actualizado_en'])
        return usuario


class FormularioTrabajadorEmpresa(forms.ModelForm):
    class Meta:
        model = TrabajadorEmpresa
        fields = ['nombres', 'apellidos', 'dni', 'telefono', 'cargo', 'empresa', 'activo', 'fecha_ingreso']
        labels = {
            'activo': 'Trabajador activo',
            'cargo': 'Cargo laboral',
            'fecha_ingreso': 'Fecha de ingreso',
        }
        widgets = {
            'nombres': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Nombres'}),
            'apellidos': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Apellidos'}),
            'dni': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': '12345678',
                'maxlength': '8',
                'inputmode': 'numeric',
            }),
            'telefono': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': '9XXXXXXXX',
                'maxlength': '9',
                'inputmode': 'numeric',
            }),
            'cargo': forms.Select(attrs={'class': SELECT_CLASS}),
            'empresa': forms.Select(attrs={'class': SELECT_CLASS}),
            'activo': forms.CheckboxInput(attrs={
                'class': 'h-5 w-5 rounded border-slate-300 text-orange-600 focus:ring-orange-500',
            }),
            'fecha_ingreso': forms.DateInput(attrs={'class': INPUT_CLASS, 'type': 'date'}),
        }

    def __init__(self, *args, creado_por=None, **kwargs):
        self.creado_por = creado_por
        super().__init__(*args, **kwargs)
        self.fields['empresa'].queryset = Empresa.objects.filter(activo=True).order_by('nombre')
        self.fields['activo'].initial = True
        if creado_por and creado_por.rol != RolUsuario.SUPER_ADMIN and creado_por.empresa:
            self.fields['empresa'].queryset = Empresa.objects.filter(pk=creado_por.empresa_id)
            self.fields['empresa'].initial = creado_por.empresa
            self.fields['empresa'].disabled = True

    def clean_dni(self):
        dni = self.cleaned_data.get('dni', '').strip()
        if not dni.isdigit() or len(dni) != 8:
            raise forms.ValidationError('El DNI debe tener exactamente 8 digitos.')
        if TrabajadorEmpresa.objects.filter(dni=dni).exists():
            raise forms.ValidationError('Este DNI ya esta registrado como trabajador.')
        return dni

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono', '').strip()
        if telefono and (not telefono.isdigit() or len(telefono) != 9):
            raise forms.ValidationError('El telefono debe tener exactamente 9 digitos.')
        return telefono

    def clean(self):
        cleaned = super().clean()

        if self.creado_por and self.creado_por.rol != RolUsuario.SUPER_ADMIN:
            if self.creado_por.empresa:
                cleaned['empresa'] = self.creado_por.empresa
            else:
                self.add_error('empresa', 'Tu usuario administrador no tiene una empresa asignada.')
        return cleaned

    def save(self, commit=True):
        trabajador = super().save(commit=False)
        if self.creado_por and self.creado_por.rol != RolUsuario.SUPER_ADMIN:
            trabajador.empresa = self.creado_por.empresa
        trabajador.tiene_acceso_sistema = bool(trabajador.usuario_id)
        if commit:
            trabajador.save()
        return trabajador


class RolSistemaForm(forms.ModelForm):
    permisos = forms.ModelMultipleChoiceField(
        queryset=PermisoSistema.objects.filter(activo=True).order_by('modulo', 'nombre'),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'rounded border-slate-300 text-orange-600 focus:ring-orange-500'}),
        label='Permisos del rol',
    )

    class Meta:
        model = RolSistema
        fields = ['nombre', 'codigo', 'descripcion', 'activo', 'permisos']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Ej: Administrador'}),
            'codigo': forms.Select(attrs={'class': SELECT_CLASS}),
            'descripcion': forms.Textarea(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Describe el alcance de este rol',
                'rows': 3,
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'h-5 w-5 rounded border-slate-300 text-orange-600 focus:ring-orange-500',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['activo'].initial = True
        usados = set(RolSistema.objects.values_list('codigo', flat=True))
        if self.instance and self.instance.pk:
            usados.discard(self.instance.codigo)
        choices = [
            choice for choice in RolSistema.CODIGOS_SISTEMA
            if choice[0] not in usados or (self.instance and self.instance.codigo == choice[0])
        ]
        self.fields['codigo'].choices = choices


class PermisoSistemaForm(forms.ModelForm):
    class Meta:
        model = PermisoSistema
        fields = ['nombre', 'codigo', 'modulo', 'descripcion', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Ej: Gestionar boletos'}),
            'codigo': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'gestionar_boletos'}),
            'modulo': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Ej: Boletos'}),
            'descripcion': forms.Textarea(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Describe que permite este permiso',
                'rows': 3,
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'h-5 w-5 rounded border-slate-300 text-orange-600 focus:ring-orange-500',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['activo'].initial = True


class ViajePanelForm(forms.ModelForm):
    class Meta:
        model = Viaje
        fields = ['ruta', 'fecha_salida', 'fecha_llegada_estimada', 'bus', 'precio']
        labels = {
            'ruta': 'Ruta',
            'fecha_salida': 'Fecha y hora de salida',
            'fecha_llegada_estimada': 'Fecha y hora de llegada',
            'bus': 'Bus asignado',
            'precio': 'Precio del pasaje',
        }
        widgets = {
            'ruta': forms.Select(attrs={'class': SELECT_CLASS}),
            'fecha_salida': forms.DateTimeInput(attrs={'class': INPUT_CLASS, 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'fecha_llegada_estimada': forms.DateTimeInput(attrs={'class': INPUT_CLASS, 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'bus': forms.Select(attrs={'class': SELECT_CLASS}),
            'precio': forms.NumberInput(attrs={'class': INPUT_CLASS, 'step': '0.01', 'min': '0'}),
        }

    def __init__(self, *args, creado_por=None, **kwargs):
        self.creado_por = creado_por
        super().__init__(*args, **kwargs)
        self.fields['ruta'].queryset = Ruta.objects.filter(
            activo=True,
            origen__in=CIUDADES_ACTIVAS_DB,
            destino__in=CIUDADES_ACTIVAS_DB,
        ).order_by('origen', 'destino')
        buses = Bus.objects.filter(activo=True).select_related('empresa').order_by('empresa__nombre', 'placa')
        if creado_por and creado_por.rol != RolUsuario.SUPER_ADMIN and creado_por.empresa:
            buses = buses.filter(empresa=creado_por.empresa)
        self.fields['bus'].queryset = buses
        self.fields['fecha_salida'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['fecha_llegada_estimada'].input_formats = ['%Y-%m-%dT%H:%M']

    def clean(self):
        cleaned = super().clean()
        salida = cleaned.get('fecha_salida')
        llegada = cleaned.get('fecha_llegada_estimada')
        bus = cleaned.get('bus')

        if salida and llegada and llegada <= salida:
            self.add_error('fecha_llegada_estimada', 'La llegada debe ser posterior a la salida.')

        if self.creado_por and self.creado_por.rol != RolUsuario.SUPER_ADMIN and self.creado_por.empresa and bus:
            if bus.empresa_id != self.creado_por.empresa_id:
                self.add_error('bus', 'Solo puedes programar buses de tu empresa.')

        return cleaned


class VenderBoletoPanelForm(forms.Form):
    viaje = forms.ModelChoiceField(
        queryset=Viaje.objects.none(),
        label='Viaje disponible',
        widget=forms.Select(attrs={'class': SELECT_CLASS}),
    )
    numero_asiento = forms.IntegerField(
        label='Asiento',
        min_value=1,
        widget=forms.NumberInput(attrs={'class': INPUT_CLASS, 'min': '1'}),
    )
    nombres = forms.CharField(
        label='Nombres',
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Nombres del pasajero'}),
    )
    apellidos = forms.CharField(
        label='Apellidos',
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Apellidos del pasajero'}),
    )
    dni = forms.CharField(
        label='DNI',
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'maxlength': '12', 'placeholder': 'DNI / CE'}),
    )
    telefono = forms.CharField(
        label='Telefono',
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'maxlength': '15', 'placeholder': 'Telefono'}),
    )
    correo = forms.EmailField(
        label='Correo opcional',
        required=False,
        widget=forms.EmailInput(attrs={'class': INPUT_CLASS, 'placeholder': 'correo@ejemplo.com'}),
    )
    metodo_pago = forms.ChoiceField(
        label='Metodo de pago',
        choices=MetodoPagoBoleto.choices,
        widget=forms.Select(attrs={'class': SELECT_CLASS}),
    )
    monto_pagado = forms.DecimalField(
        label='Monto pagado',
        max_digits=8,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': INPUT_CLASS, 'step': '0.01', 'min': '0'}),
    )
    estado_pago = forms.ChoiceField(
        label='Estado de pago',
        choices=EstadoPagoBoleto.choices,
        widget=forms.Select(attrs={'class': SELECT_CLASS}),
    )

    def __init__(self, *args, creado_por=None, **kwargs):
        self.creado_por = creado_por
        super().__init__(*args, **kwargs)
        viajes = (
            Viaje.objects
            .filter(
                estado__in=[EstadoViaje.PROGRAMADO, EstadoViaje.EN_EMBARQUE],
                ruta__activo=True,
                ruta__origen__in=CIUDADES_ACTIVAS_DB,
                ruta__destino__in=CIUDADES_ACTIVAS_DB,
            )
            .select_related('ruta', 'bus', 'bus__empresa')
            .order_by('fecha_salida')
        )
        if creado_por and creado_por.rol != RolUsuario.SUPER_ADMIN and creado_por.empresa:
            viajes = viajes.filter(bus__empresa=creado_por.empresa)
        self.fields['viaje'].queryset = viajes

    def clean_dni(self):
        dni = self.cleaned_data.get('dni', '').strip()
        if not dni:
            raise forms.ValidationError('Ingresa el documento del pasajero.')
        return dni

    def clean(self):
        cleaned = super().clean()
        viaje = cleaned.get('viaje')
        asiento = cleaned.get('numero_asiento')
        monto = cleaned.get('monto_pagado')

        if viaje and asiento:
            if asiento > viaje.bus.capacidad:
                self.add_error('numero_asiento', f'El bus solo tiene {viaje.bus.capacidad} asientos.')
            ocupado = Boleto.objects.filter(viaje=viaje, numero_asiento=asiento).exclude(
                estado__in=[EstadoBoleto.CANCELADO, EstadoBoleto.ANULADO, EstadoBoleto.REPROGRAMADO]
            ).exists()
            if ocupado:
                self.add_error('numero_asiento', 'Este asiento ya esta vendido o reservado.')

        if viaje and monto is not None and monto <= 0:
            self.add_error('monto_pagado', 'El monto debe ser mayor a cero.')

        return cleaned
