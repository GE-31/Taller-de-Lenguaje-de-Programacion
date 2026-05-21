from django.urls import path
from . import views, api

app_name = 'cuentas'

urlpatterns = [
    path('login/',    views.vista_login,    name='login'),
    path('registro/', views.vista_registro, name='registro'),
    path('logout/',   views.vista_logout,   name='logout'),
    path('mi-cuenta/', views.mi_cuenta, name='mi_cuenta'),
    path('mi-cuenta/tarjetas/<int:tarjeta_id>/principal/', views.tarjeta_principal, name='tarjeta_principal'),
    path('mi-cuenta/tarjetas/<int:tarjeta_id>/eliminar/', views.eliminar_tarjeta, name='eliminar_tarjeta'),
    # API endpoints para pasajeros
    path('api/pasajeros/buscar-por-dni/', api.buscar_pasajero_por_dni, name='buscar_pasajero_dni'),
    path('api/pasajeros/guardar/', api.guardar_actualizar_pasajero, name='guardar_pasajero'),
    path('api/pasajeros/<int:pasajero_id>/', api.obtener_pasajero, name='obtener_pasajero'),
]
