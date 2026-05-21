from django import forms

from apps.rutas.models import Ruta

from .models import CondicionPagoEncomienda, Encomienda, EstadoEncomienda


class EncomiendaForm(forms.ModelForm):
    class Meta:
        model = Encomienda
        fields = [
            'remitente_nombres',
            'remitente_dni',
            'remitente_telefono',
            'destinatario_nombres',
            'destinatario_dni',
            'destinatario_telefono',
            'clave_recojo',
            'origen',
            'destino',
            'descripcion',
            'peso_kg',
            'monto',
            'condicion_pago',
            'metodo_pago',
        ]
        widgets = {
            'descripcion': forms.TextInput(attrs={'placeholder': 'Ej. Caja mediana, documentos, paquete'}),
            'clave_recojo': forms.TextInput(attrs={
                'maxlength': '4',
                'inputmode': 'numeric',
                'placeholder': '4 digitos',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_class = (
            'w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-800 '
            'focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100'
        )
        ciudades = sorted({
            ciudad
            for ruta in Ruta.objects.filter(activo=True).values('origen', 'destino')
            for ciudad in (ruta['origen'], ruta['destino'])
            if ciudad
        })
        opciones_ciudad = [('', 'Selecciona ciudad')] + [(ciudad, ciudad) for ciudad in ciudades]
        self.fields['origen'] = forms.ChoiceField(
            choices=opciones_ciudad,
            widget=forms.Select(attrs={'class': base_class}),
        )
        self.fields['destino'] = forms.ChoiceField(
            choices=opciones_ciudad,
            widget=forms.Select(attrs={'class': base_class}),
        )
        self.fields['condicion_pago'].choices = [
            (CondicionPagoEncomienda.PAGADO_ORIGEN, 'Pagado en agencia'),
            (CondicionPagoEncomienda.COBRO_DESTINO, 'Paga al recoger'),
        ]
        for field in self.fields.values():
            field.widget.attrs['class'] = base_class

    def clean(self):
        cleaned = super().clean()
        condicion_pago = cleaned.get('condicion_pago')
        metodo_pago = cleaned.get('metodo_pago')
        if condicion_pago == CondicionPagoEncomienda.PAGADO_ORIGEN and not metodo_pago:
            self.add_error('metodo_pago', 'Selecciona el metodo de pago.')
        if condicion_pago == CondicionPagoEncomienda.COBRO_DESTINO:
            cleaned['metodo_pago'] = ''
        origen = cleaned.get('origen')
        destino = cleaned.get('destino')
        if origen and destino:
            if origen == destino:
                self.add_error('destino', 'El origen y destino no pueden ser iguales.')
            elif not Ruta.objects.filter(origen=origen, destino=destino, activo=True).exists():
                self.add_error('destino', 'No tenemos esa ruta disponible para encomiendas.')
        return cleaned

    def clean_clave_recojo(self):
        clave = (self.cleaned_data.get('clave_recojo') or '').strip()
        if not clave:
            return clave
        if not clave.isdigit() or len(clave) != 4:
            raise forms.ValidationError('La clave debe tener 4 digitos numericos.')
        qs = Encomienda.objects.exclude(estado=EstadoEncomienda.ENTREGADO).filter(clave_recojo=clave)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Esta clave ya esta en uso. Ingresa otra clave de 4 digitos.')
        return clave


class RecojoBuscarForm(forms.Form):
    dni = forms.CharField(
        label='DNI de quien recoge',
        max_length=8,
        widget=forms.TextInput(attrs={
            'class': 'w-full rounded-xl border border-slate-200 px-4 py-3 text-sm font-semibold outline-none focus:border-orange-300 focus:ring-4 focus:ring-orange-100',
            'maxlength': '8',
            'inputmode': 'numeric',
            'placeholder': 'DNI',
        }),
    )
    clave = forms.CharField(
        label='Clave de 4 digitos',
        max_length=4,
        widget=forms.TextInput(attrs={
            'class': 'w-full rounded-xl border border-slate-200 px-4 py-3 text-sm font-semibold outline-none focus:border-orange-300 focus:ring-4 focus:ring-orange-100',
            'maxlength': '4',
            'inputmode': 'numeric',
            'placeholder': 'Clave',
        }),
    )

    def clean_dni(self):
        dni = self.cleaned_data['dni'].strip()
        if not dni.isdigit() or len(dni) != 8:
            raise forms.ValidationError('Ingresa un DNI valido de 8 digitos.')
        return dni

    def clean_clave(self):
        clave = self.cleaned_data['clave'].strip()
        if not clave.isdigit() or len(clave) != 4:
            raise forms.ValidationError('La clave debe tener 4 digitos numericos.')
        return clave


class RecojoCobroForm(forms.Form):
    metodo_pago = forms.ChoiceField(
        label='Metodo de pago',
        choices=[
            ('efectivo', 'Efectivo'),
            ('yape', 'Yape'),
            ('plin', 'Plin'),
            ('tarjeta', 'Tarjeta'),
            ('transferencia', 'Transferencia'),
        ],
        widget=forms.Select(attrs={
            'class': 'w-full rounded-xl border border-slate-200 px-4 py-3 text-sm font-semibold outline-none focus:border-orange-300 focus:ring-4 focus:ring-orange-100',
        }),
    )


class RecojoEntregaForm(forms.Form):
    recogido_por_nombres = forms.CharField(
        label='Nombre de quien recoge',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'w-full rounded-xl border border-slate-200 px-4 py-3 text-sm font-semibold outline-none focus:border-orange-300 focus:ring-4 focus:ring-orange-100',
        }),
    )
