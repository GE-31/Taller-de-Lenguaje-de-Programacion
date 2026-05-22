from django.urls import path
from . import views

app_name = 'viajes'

urlpatterns = [
    path('buscar/',                   views.buscar,       name='buscar'),
    path('asientos/<int:viaje_id>/',  views.asientos_json, name='asientos'),
    path('pagar/<int:viaje_id>/',     views.pagar,        name='pagar'),
    path('pagos/yape/crear/',         views.crear_pago_yape, name='crear_pago_yape'),
    path('pagos/yape/<uuid:codigo>/estado/', views.estado_pago_yape, name='estado_pago_yape'),
    path('pagos/yape/<uuid:codigo>/simular/', views.simular_pago_yape, name='simular_pago_yape'),
    path('pagos/yape/<uuid:codigo>/confirmar/', views.confirmar_pago_yape, name='confirmar_pago_yape'),
    path('confirmar/',                views.confirmar,    name='confirmar'),
    path('confirmacion/<uuid:codigo>/', views.confirmacion, name='confirmacion'),
]
