from django.urls import path

from . import views

app_name = 'encomiendas'

urlpatterns = [
    path('panel/', views.panel_encomiendas, name='panel_lista'),
    path('panel/<int:encomienda_id>/estado/', views.cambiar_estado, name='cambiar_estado'),
    path('api/crear/', views.api_crear, name='api_crear'),
    path('api/rastreo/<str:codigo>/', views.api_rastrear, name='api_rastrear'),
    path('api/rastreo-orden/', views.api_rastrear_orden, name='api_rastrear_orden'),
]
