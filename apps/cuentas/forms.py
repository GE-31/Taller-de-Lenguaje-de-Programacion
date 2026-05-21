import re

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as CoreValidationError
from .models import Usuario, Pasajero, TarjetaCliente

# ── Clase de input base (reutilizable) ───────────────────────────────────────
_INPUT = (
    'block w-full py-3 px-4 rounded-xl border border-gray-200 bg-gray-50 '
    'text-sm text-gray-900 placeholder-gray-400 '
    'focus:outline-none focus:ring-2 focus:ring-orange-400 '
    'focus:border-transparent focus:bg-white transition-all duration-200'
)
_INPUT_ICON = (
    'block w-full py-3 pl-11 pr-4 rounded-xl border border-gray-200 bg-gray-50 '
    'text-sm text-gray-900 placeholder-gray-400 '
    'focus:outline-none focus:ring-2 focus:ring-orange-400 '
    'focus:border-transparent focus:bg-white transition-all duration-200'
)
_INPUT_ICON_RIGHT = (
    'block w-full py-3 pl-11 pr-12 rounded-xl border border-gray-200 bg-gray-50 '
    'text-sm text-gray-900 placeholder-gray-400 '
    'focus:outline-none focus:ring-2 focus:ring-orange-400 '
    'focus:border-transparent focus:bg-white transition-all duration-200'
)


class FormularioLogin(forms.Form):
    email = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={
            'class': _INPUT_ICON,
            'placeholder': 'correo@ejemplo.com',
            'autofocus': True,
            'autocomplete': 'email',
            'id': 'id_email_login',
        }),
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': _INPUT_ICON_RIGHT,
            'placeholder': '••••••••',
            'autocomplete': 'current-password',
            'id': 'id_password_login',
        }),
    )
    recordar = forms.BooleanField(required=False, label='Mantener sesión iniciada')

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.usuario_autenticado = None

    def clean(self):
        email    = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')
        if email and password:
            usuario = authenticate(self.request, username=email, password=password)
            if usuario is None:
                raise forms.ValidationError('Correo o contraseña incorrectos.')
            if not usuario.is_active:
                raise forms.ValidationError('Esta cuenta está desactivada.')
            self.usuario_autenticado = usuario
        return self.cleaned_data


class FormularioRegistro(forms.ModelForm):
    password1 = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': _INPUT_ICON_RIGHT,
            'placeholder': 'Mínimo 8 caracteres',
            'autocomplete': 'new-password',
            'id': 'id_password1',
        }),
    )
    password2 = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={
            'class': _INPUT_ICON_RIGHT,
            'placeholder': 'Repite tu contraseña',
            'autocomplete': 'new-password',
            'id': 'id_password2',
        }),
    )

    class Meta:
        model  = Usuario
        fields = ['nombres', 'apellidos', 'email', 'dni', 'telefono']
        widgets = {
            'nombres': forms.TextInput(attrs={
                'class': _INPUT_ICON,
                'placeholder': 'Tus nombres',
                'autocomplete': 'given-name',
            }),
            'apellidos': forms.TextInput(attrs={
                'class': _INPUT_ICON,
                'placeholder': 'Tus apellidos',
                'autocomplete': 'family-name',
            }),
            'email': forms.EmailInput(attrs={
                'class': _INPUT_ICON,
                'placeholder': 'correo@ejemplo.com',
                'autocomplete': 'email',
            }),
            'dni': forms.TextInput(attrs={
                'class': _INPUT_ICON,
                'placeholder': '12345678',
                'maxlength': '8',
                'autocomplete': 'off',
                'inputmode': 'numeric',
            }),
            'telefono': forms.TextInput(attrs={
                'class': _INPUT_ICON,
                'placeholder': '9XXXXXXXX',
                'autocomplete': 'tel',
                'inputmode': 'tel',
                'maxlength': '9',
            }),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower()
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError('Este correo ya está registrado. ¿Quieres iniciar sesión?')
        return email

    def clean_dni(self):
        dni = self.cleaned_data.get('dni', '').strip()
        if not dni.isdigit() or len(dni) != 8:
            raise forms.ValidationError('El DNI debe tener exactamente 8 dígitos numéricos.')
        if Usuario.objects.filter(dni=dni).exists():
            raise forms.ValidationError('Este DNI ya está registrado.')
        return dni

    def clean_telefono(self):
        tel = self.cleaned_data.get('telefono', '').strip()
        if tel:
            if not tel.isdigit() or len(tel) != 9:
                raise forms.ValidationError('El teléfono debe tener exactamente 9 dígitos.')
        return tel

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1', '')
        p2 = cleaned.get('password2', '')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Las contraseñas no coinciden.')
        if p1:
            try:
                validate_password(p1)
            except CoreValidationError as e:
                self.add_error('password1', list(e.messages))
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.rol = 'pasajero'
        if commit:
            user.save()
            Pasajero.objects.update_or_create(
                dni=user.dni,
                defaults={
                    'nombres': user.nombres,
                    'apellidos': user.apellidos,
                    'telefono': user.telefono or '',
                    'correo': user.email,
                },
            )
        return user


class FormularioPerfilUsuario(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['nombres', 'apellidos', 'email', 'telefono']
        widgets = {
            'nombres': forms.TextInput(attrs={'class': _INPUT, 'autocomplete': 'given-name'}),
            'apellidos': forms.TextInput(attrs={'class': _INPUT, 'autocomplete': 'family-name'}),
            'email': forms.EmailInput(attrs={'class': _INPUT, 'autocomplete': 'email'}),
            'telefono': forms.TextInput(attrs={
                'class': _INPUT,
                'placeholder': '9XXXXXXXX',
                'maxlength': '9',
                'inputmode': 'numeric',
                'autocomplete': 'tel',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.get('instance')
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        qs = Usuario.objects.filter(email=email)
        if self.usuario:
            qs = qs.exclude(pk=self.usuario.pk)
        if qs.exists():
            raise forms.ValidationError('Este correo ya esta registrado por otra cuenta.')
        return email

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono', '').strip()
        if telefono and (not telefono.isdigit() or len(telefono) != 9):
            raise forms.ValidationError('El telefono debe tener exactamente 9 digitos.')
        return telefono


class FormularioTarjetaCliente(forms.Form):
    titular = forms.CharField(
        max_length=120,
        widget=forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'Nombre como aparece en la tarjeta'}),
    )
    numero = forms.CharField(
        max_length=19,
        widget=forms.TextInput(attrs={
            'class': _INPUT,
            'placeholder': '0000 0000 0000 0000',
            'maxlength': '19',
            'inputmode': 'numeric',
            'autocomplete': 'cc-number',
        }),
    )
    vencimiento = forms.CharField(
        max_length=5,
        widget=forms.TextInput(attrs={
            'class': _INPUT,
            'placeholder': 'MM/AA',
            'maxlength': '5',
            'autocomplete': 'cc-exp',
        }),
    )

    def clean_numero(self):
        numero = ''.join(ch for ch in self.cleaned_data.get('numero', '') if ch.isdigit())
        if len(numero) < 13 or len(numero) > 16:
            raise forms.ValidationError('Ingresa un numero de tarjeta valido para la simulacion.')
        return numero

    def clean_vencimiento(self):
        vencimiento = self.cleaned_data.get('vencimiento', '').strip()
        if not re.fullmatch(r'\d{2}/\d{2}', vencimiento):
            raise forms.ValidationError('Usa el formato MM/AA.')
        mes = int(vencimiento[:2])
        anio = int(vencimiento[3:])
        if mes < 1 or mes > 12:
            raise forms.ValidationError('El mes debe estar entre 01 y 12.')
        return vencimiento

    def marca_tarjeta(self):
        numero = self.cleaned_data['numero']
        if numero.startswith('4'):
            return 'Visa'
        if numero[:2] in {'51', '52', '53', '54', '55'} or 2221 <= int(numero[:4]) <= 2720:
            return 'Mastercard'
        if numero.startswith(('34', '37')):
            return 'American Express'
        return 'Tarjeta'

    def save(self, usuario):
        vencimiento = self.cleaned_data['vencimiento']
        mes = int(vencimiento[:2])
        anio = 2000 + int(vencimiento[3:])
        if not usuario.tarjetas.exists():
            es_principal = True
        else:
            es_principal = False
        return TarjetaCliente.objects.create(
            usuario=usuario,
            titular=self.cleaned_data['titular'].strip(),
            marca=self.marca_tarjeta(),
            ultimos_4=self.cleaned_data['numero'][-4:],
            mes_expiracion=mes,
            anio_expiracion=anio,
            es_principal=es_principal,
        )


# ══════════════════════════════════════════════════════════════════════════════
# FORMULARIO PARA PASAJEROS (sin autenticación)
# ══════════════════════════════════════════════════════════════════════════════

class PasajeroForm(forms.ModelForm):
    """
    Formulario para capturar/editar datos de pasajeros que compran boletos.
    Se utiliza en el flujo de compra de pasajes sin necesidad de autenticación.
    
    Seguridad:
    - Valida que DNI tenga exactamente 8 dígitos
    - Valida email correcto
    - Valida teléfono con formato correcto
    - Sanitiza espacios en blanco
    """

    class Meta:
        model = Pasajero
        fields = ['dni', 'nombres', 'apellidos', 'genero', 'fecha_nacimiento', 'telefono', 'correo']
        widgets = {
            'dni': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent bg-blue-50 focus:bg-white transition-all',
                'placeholder': 'Ej: 71852009',
                'maxlength': '8',
                'inputmode': 'numeric',
                'autocomplete': 'off',
                'pattern': '[0-9]{8}',
            }),
            'nombres': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all',
                'placeholder': 'Ej: Juan',
                'maxlength': '150',
                'autocomplete': 'given-name',
            }),
            'apellidos': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all',
                'placeholder': 'Ej: Pérez García',
                'maxlength': '150',
                'autocomplete': 'family-name',
            }),
            'genero': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all',
            }),
            'fecha_nacimiento': forms.DateInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all',
                'type': 'date',
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all',
                'placeholder': 'Ej: 967271234',
                'maxlength': '9',
                'inputmode': 'tel',
                'autocomplete': 'tel',
            }),
            'correo': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all',
                'placeholder': 'Ej: correo@ejemplo.com',
                'autocomplete': 'email',
            }),
        }

    def clean_dni(self):
        """Valida que el DNI tenga exactamente 8 dígitos"""
        dni = self.cleaned_data.get('dni', '').strip()
        if not dni:
            raise forms.ValidationError('El DNI es obligatorio.')
        if not dni.isdigit():
            raise forms.ValidationError('El DNI solo debe contener números.')
        if len(dni) != 8:
            raise forms.ValidationError('El DNI debe tener exactamente 8 dígitos.')
        return dni

    def clean_nombres(self):
        """Valida y sanitiza nombres"""
        nombres = self.cleaned_data.get('nombres', '').strip()
        if not nombres:
            raise forms.ValidationError('Los nombres son obligatorios.')
        if len(nombres) < 2:
            raise forms.ValidationError('Los nombres deben tener al menos 2 caracteres.')
        if len(nombres) > 150:
            raise forms.ValidationError('Los nombres no pueden exceder 150 caracteres.')
        return nombres

    def clean_apellidos(self):
        """Valida y sanitiza apellidos"""
        apellidos = self.cleaned_data.get('apellidos', '').strip()
        if not apellidos:
            raise forms.ValidationError('Los apellidos son obligatorios.')
        if len(apellidos) < 2:
            raise forms.ValidationError('Los apellidos deben tener al menos 2 caracteres.')
        if len(apellidos) > 150:
            raise forms.ValidationError('Los apellidos no pueden exceder 150 caracteres.')
        return apellidos

    def clean_correo(self):
        """Valida email"""
        correo = self.cleaned_data.get('correo', '').strip().lower()
        if correo and '@' not in correo:
            raise forms.ValidationError('Ingresa un correo electrónico válido.')
        return correo

    def clean_telefono(self):
        """Valida teléfono"""
        telefono = self.cleaned_data.get('telefono', '').strip()
        if telefono:
            if not telefono.isdigit():
                raise forms.ValidationError('El teléfono solo debe contener números.')
            if len(telefono) != 9:
                raise forms.ValidationError('El teléfono debe tener exactamente 9 dígitos.')
        return telefono

    def clean_genero(self):
        """Valida género"""
        genero = self.cleaned_data.get('genero', '').strip()
        valid_generos = ['M', 'F', 'O']
        if genero and genero not in valid_generos:
            raise forms.ValidationError('Selecciona un género válido.')
        return genero
