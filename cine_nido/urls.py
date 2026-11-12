from django.urls import path

from . import views

urlpatterns = [
    # Público
    path("", views.cartelera, name="cartelera"),
    path("pelicula/<int:pelicula_id>/", views.pelicula_detalle, name="pelicula_detalle"),

    # Compra
    path("funcion/<int:funcion_id>/asientos/", views.asientos, name="asientos"),
    path("compra/correo/", views.compra_correo, name="compra_correo"),
    path("confiteria/", views.confiteria, name="confiteria"),
    path("pago/", views.pago, name="pago"),
    path("entrada/<int:compra_id>/", views.entrada, name="entrada"),

    # Cuenta
    path("cuenta/ingresar/", views.ingresar, name="ingresar"),
    path("cuenta/registro/", views.registro, name="registro"),
    path("cuenta/salir/", views.salir, name="salir"),
    path("cuenta/recuperar/", views.recuperar, name="recuperar"),
    path("cuenta/mis-compras/", views.mis_compras, name="mis_compras"),

    # Panel interno (validar va antes que la ruta genérica)
    path("panel/", views.panel_dashboard, name="panel_dashboard"),
    path("panel/validar/", views.panel_validar, name="panel_validar"),
    path("panel/ventas/<int:pk>/", views.panel_venta_detalle, name="panel_venta_detalle"),
    path("panel/<str:seccion>/nuevo/", views.panel_formulario, name="panel_nuevo"),
    path("panel/<str:seccion>/<int:pk>/editar/", views.panel_formulario, name="panel_editar"),
    path("panel/<str:seccion>/", views.panel_listado, name="panel_listado"),

    # API REST (JSON)
    path("api/salas/", views.api_salas, name="api_salas"),
    path("api/salas/<int:sala_id>/", views.api_sala_detalle, name="api_sala_detalle"),
    path("api/peliculas/", views.api_peliculas, name="api_peliculas"),
    path("api/peliculas/<int:pelicula_id>/", views.api_pelicula_detalle, name="api_pelicula_detalle"),
    path("api/funciones/", views.api_funciones, name="api_funciones"),
    path("api/funciones/<int:funcion_id>/", views.api_funcion_detalle, name="api_funcion_detalle"),
    path("api/funciones/<int:funcion_id>/asientos/", views.api_funcion_asientos, name="api_funcion_asientos"),
    path("api/funciones/<int:funcion_id>/reservar/", views.api_reservar_asientos, name="api_reservar_asientos"),
    path("api/confiteria/", views.api_confiteria, name="api_confiteria"),
    path("api/confiteria/<int:producto_id>/", views.api_confiteria_detalle, name="api_confiteria_detalle"),
    path("api/compras/", views.api_compras, name="api_compras"),
    path("api/compras/<int:compra_id>/", views.api_compra_detalle, name="api_compra_detalle"),
    path("api/validar-entrada/", views.api_validar_entrada, name="api_validar_entrada"),
]
