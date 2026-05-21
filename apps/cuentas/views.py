from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import (
    FormularioLogin,
    FormularioPerfilUsuario,
    FormularioRegistro,
    FormularioTarjetaCliente,
)
from .models import Pasajero, TarjetaCliente

ROLES_PANEL = frozenset({
    'admin',
    'vendedor',
    'encomiendas',
    'conductor',
    'admin_empresa',
    'super_admin',
})


def vista_login(request):
    siguiente = request.GET.get('next', '').strip()
    siguiente_valido = siguiente if url_has_allowed_host_and_scheme(
        siguiente,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ) else ''

    if request.user.is_authenticated:
        if request.user.rol in ROLES_PANEL:
            return redirect('panel:dashboard')
        return redirect(siguiente_valido or 'publico:inicio')

    form = FormularioLogin(request.POST or None, request=request)
    if request.method == 'POST' and form.is_valid():
        user = form.usuario_autenticado
        if user.rol in ROLES_PANEL:
            form.add_error(None, 'Este acceso es para clientes. Usa el login del panel de trabajadores.')
            return render(request, 'cuentas/login.html', {
                'form': form,
                'beneficios': [
                    'Compra con o sin cuenta',
                    'Boleto digital al instante',
                    'Elige tu asiento favorito',
                    'Pago con Yape, Plin o tarjeta',
                ],
            })
        login(request, user)
        if form.cleaned_data.get('recordar'):
            request.session.set_expiry(60 * 60 * 24 * 30)
        else:
            request.session.set_expiry(0)
        return redirect(siguiente_valido or 'publico:inicio')

    return render(request, 'cuentas/login.html', {
        'form': form,
        'beneficios': [
            'Compra con o sin cuenta',
            'Boleto digital al instante',
            'Elige tu asiento favorito',
            'Pago con Yape, Plin o tarjeta',
        ],
    })


def vista_registro(request):
    if request.user.is_authenticated:
        return redirect('publico:inicio')

    form = FormularioRegistro(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        request.session.set_expiry(0)
        return redirect('publico:inicio')

    return render(request, 'cuentas/registro.html', {
        'form': form,
        'ventajas': [
            'Historial de viajes y boletos',
            'Notificaciones de tus compras',
            'Datos pre-llenados en tu próxima compra',
        ],
    })


def vista_logout(request):
    logout(request)
    response = redirect('publico:inicio')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    return response


@login_required(login_url='cuentas:login')
def mi_cuenta(request):
    if request.user.rol in ROLES_PANEL:
        return redirect('panel:dashboard')

    perfil_form = FormularioPerfilUsuario(instance=request.user, prefix='perfil')
    tarjeta_form = FormularioTarjetaCliente(prefix='tarjeta')

    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'perfil':
            perfil_form = FormularioPerfilUsuario(request.POST, instance=request.user, prefix='perfil')
            if perfil_form.is_valid():
                usuario = perfil_form.save()
                Pasajero.objects.update_or_create(
                    dni=usuario.dni,
                    defaults={
                        'nombres': usuario.nombres,
                        'apellidos': usuario.apellidos,
                        'telefono': usuario.telefono or '',
                        'correo': usuario.email,
                    },
                )
                messages.success(request, 'Tus datos se actualizaron correctamente.')
                return redirect('cuentas:mi_cuenta')

        elif accion == 'tarjeta':
            tarjeta_form = FormularioTarjetaCliente(request.POST, prefix='tarjeta')
            if tarjeta_form.is_valid():
                tarjeta_form.save(request.user)
                messages.success(request, 'Tarjeta agregada para pagos simulados.')
                return redirect('cuentas:mi_cuenta')

    return render(request, 'cuentas/mi_cuenta.html', {
        'perfil_form': perfil_form,
        'tarjeta_form': tarjeta_form,
        'tarjetas': request.user.tarjetas.all(),
    })


@login_required(login_url='cuentas:login')
def tarjeta_principal(request, tarjeta_id):
    if request.method != 'POST':
        return redirect('cuentas:mi_cuenta')
    tarjeta = get_object_or_404(TarjetaCliente, id=tarjeta_id, usuario=request.user)
    request.user.tarjetas.update(es_principal=False)
    tarjeta.es_principal = True
    tarjeta.save(update_fields=['es_principal'])
    messages.success(request, 'Tarjeta principal actualizada.')
    return redirect('cuentas:mi_cuenta')


@login_required(login_url='cuentas:login')
def eliminar_tarjeta(request, tarjeta_id):
    if request.method != 'POST':
        return redirect('cuentas:mi_cuenta')
    tarjeta = get_object_or_404(TarjetaCliente, id=tarjeta_id, usuario=request.user)
    era_principal = tarjeta.es_principal
    tarjeta.delete()
    if era_principal:
        siguiente = request.user.tarjetas.first()
        if siguiente:
            siguiente.es_principal = True
            siguiente.save(update_fields=['es_principal'])
    messages.success(request, 'Tarjeta eliminada.')
    return redirect('cuentas:mi_cuenta')
