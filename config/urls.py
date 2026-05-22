from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.viajes import views as viajes_views
from apps.encomiendas import views as encomiendas_views

urlpatterns = [
    path('admin/',   admin.site.urls),
    path('pago/<uuid:codigo>/', viajes_views.simular_pago_yape, name='pago_yape_lan'),
    path('pagalo/web/', encomiendas_views.pagalo_web, name='pagalo_web'),
    path('',         include('apps.publico.urls')),
    path('',         include('apps.cuentas.urls')),
    path('panel/',   include('apps.panel.urls')),
    path('viajes/',  include('apps.viajes.urls')),
    path('ventas/',  include('apps.ventas.urls')),
    path('encomiendas/', include('apps.encomiendas.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
