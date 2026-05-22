from django.urls import path
from . import views

app_name = 'ventas'

urlpatterns = [
    path('boleta/<uuid:codigo_boleto>/', views.detalle_boleta, name='detalle_boleta'),
    path('boleta/<uuid:codigo_boleto>/descargar/', views.descargar_boleta, name='descargar_boleta'),
    path('boleta/<uuid:codigo_boleto>/imprimir/', views.imprimir_boleta, name='imprimir_boleta'),
]
