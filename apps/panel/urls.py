from django.urls import path
from . import views
from apps.encomiendas import views as encomiendas_views

app_name = 'panel'

urlpatterns = [
    path('',                           views.dashboard,              name='dashboard'),
    path('viajes/',                    views.viajes,                 name='viajes'),
    path('viajes/nuevo/',              views.viaje_nuevo,            name='viaje_nuevo'),
    path('viajes/<int:viaje_id>/',     views.viaje_detalle,          name='viaje_detalle'),
    path('viajes/<int:viaje_id>/editar/', views.viaje_editar,        name='viaje_editar'),
    path('viajes/<int:viaje_id>/cancelar/', views.viaje_cancelar,    name='viaje_cancelar'),
    path('viajes/<int:viaje_id>/boletos/', views.viaje_boletos,      name='viaje_boletos'),
    path('viajes/<int:viaje_id>/pasajeros/pdf/', views.generar_pdf_pasajeros, name='generar_pdf_pasajeros'),
    path('usuarios/registrar/',        views.registrar_usuario,      name='registrar_usuario'),
    path('trabajadores/',              views.trabajadores,           name='trabajadores'),
    path('roles/',                     views.roles,                  name='roles'),
    path('roles/<int:rol_id>/editar/', views.editar_rol,             name='editar_rol'),
    path('roles/<int:rol_id>/estado/', views.cambiar_estado_rol,     name='rol_estado'),
    path('permisos/<int:permiso_id>/editar/', views.editar_permiso,         name='editar_permiso'),
    path('permisos/<int:permiso_id>/estado/', views.cambiar_estado_permiso, name='permiso_estado'),
    path('boletos/',                   views.boletos,                name='boletos'),
    path('boletos/vender/',            views.vender_boleto,          name='vender_boleto'),
    path('boletos/<int:boleto_id>/',   views.boleto_detalle,         name='boleto_detalle'),
    path('boletos/<int:boleto_id>/cancelar/', views.cancelar_boleto, name='cancelar_boleto'),
    path('boletos/<int:boleto_id>/reprogramar/', views.reprogramar_boleto, name='reprogramar_boleto'),
    path('reportes/',                  views.reportes,               name='reportes'),
    path('auditoria/',                  views.auditoria,              name='auditoria'),
    path('libro-reclamaciones/',       views.libro_reclamaciones_panel, name='libro_reclamaciones'),
    path('libro-reclamaciones/<int:reclamacion_id>/estado/', views.cambiar_estado_reclamacion, name='reclamacion_estado'),
    path('login/',                     views.vista_login_panel,      name='login'),
    path('asientos/<int:viaje_id>/',   views.seleccionar_asientos,   name='asientos'),
    path('encomiendas/',               encomiendas_views.panel_encomiendas, name='encomiendas'),
    path('encomiendas/recojo-entrega/', encomiendas_views.recojo_entrega, name='recojo_entrega'),
    path('encomiendas/<int:encomienda_id>/boleta/', encomiendas_views.boleta_encomienda, name='encomienda_boleta'),
    path('encomiendas/<int:encomienda_id>/constancia/', encomiendas_views.constancia_recojo, name='encomienda_constancia'),
    path('encomiendas/<int:encomienda_id>/estado/', encomiendas_views.cambiar_estado, name='encomienda_estado'),
]
