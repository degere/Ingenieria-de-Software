from django.urls import path

from . import views

urlpatterns = [
    # Público
    path("", views.cartelera, name="cartelera"),
    path("pelicula/<int:pelicula_id>/", views.pelicula_detalle, name="pelicula_detalle"),

    # Compra
    path("funcion/<int:funcion_id>/asientos/", views.asientos, name="asientos"),
    path("confiteria/", views.confiteria, name="confiteria"),
    path("pago/", views.pago, name="pago"),
    path("entrada/<int:compra_id>/", views.entrada, name="entrada"),

    # Cuenta
    path("cuenta/ingresar/", views.ingresar, name="ingresar"),
    path("cuenta/registro/", views.registro, name="registro"),
    path("cuenta/recuperar/", views.recuperar, name="recuperar"),
    path("cuenta/mis-compras/", views.mis_compras, name="mis_compras"),

    # Panel interno (validar va antes que la ruta genérica)
    path("panel/", views.panel_dashboard, name="panel_dashboard"),
    path("panel/validar/", views.panel_validar, name="panel_validar"),
    path("panel/<str:seccion>/", views.panel_listado, name="panel_listado"),
]
