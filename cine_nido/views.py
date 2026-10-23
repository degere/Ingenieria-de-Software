"""
VISTAS DEL FRONTEND (TEMPORALES)
--------------------------------
Cada vista solo arma un contexto con datos de datos_demo.py y renderiza su
plantilla. A medida que el backend avance, se reemplaza el uso de `demo`
por consultas reales a los modelos (Pelicula, Funcion, Asiento, etc.).
"""
from django.http import Http404
from django.shortcuts import render

from . import datos_demo as demo


# ---------------------------- Público ----------------------------

def cartelera(request):
    q = request.GET.get("q", "").strip()
    peliculas = demo.PELICULAS
    if q:
        peliculas = [p for p in peliculas if q.lower() in p["nombre"].lower() or q.lower() in p["genero"].lower()]
    return render(request, "cine_nido/cartelera.html", {
        "q": q,
        "en_cartelera": [p for p in peliculas if p["estado"] == "en_cartelera"],
        "proximos": [p for p in peliculas if p["estado"] == "proximo"],
    })


def pelicula_detalle(request, pelicula_id):
    pelicula = demo.obtener_pelicula(pelicula_id)
    if not pelicula:
        raise Http404("Película no encontrada")
    return render(request, "cine_nido/pelicula_detalle.html", {
        "pelicula": pelicula,
        "dias": demo.funciones_por_dia(pelicula_id),
    })


# ---------------------------- Compra (5 pasos) ----------------------------

def asientos(request, funcion_id):
    funcion = demo.obtener_funcion(funcion_id)
    if not funcion:
        raise Http404("Función no encontrada")
    return render(request, "cine_nido/asientos.html", {
        "funcion": funcion,
        "pelicula": demo.obtener_pelicula(funcion["pelicula_id"]),
        "mapa": demo.mapa_sala(funcion_id),
        "precios": demo.PRECIOS,
    })


def confiteria(request):
    # DEMO: valores fijos que luego saldrán de la compra en curso
    return render(request, "cine_nido/confiteria.html", {
        "categorias": demo.productos_por_categoria(),
        "resumen": {"pelicula": "Noche en el Muelle", "asientos": "D5, D6", "base": 11000},
    })


def pago(request):
    return render(request, "cine_nido/pago.html", {
        "resumen": {"pelicula": "Noche en el Muelle", "funcion": "Sala 1 · 20:30", "asientos": "D5, D6",
                    "entradas": 11000, "confiteria": 9900, "total": 20900},
    })


def entrada(request, compra_id):
    compra = next((c for c in demo.COMPRAS if c["id"] == compra_id), None)
    if not compra:
        raise Http404("Compra no encontrada")
    return render(request, "cine_nido/entrada.html", {"compra": compra})


# ---------------------------- Cuenta ----------------------------

def ingresar(request):
    return render(request, "cine_nido/ingresar.html")


def registro(request):
    return render(request, "cine_nido/registro.html")


def recuperar(request):
    return render(request, "cine_nido/recuperar.html")


def mis_compras(request):
    return render(request, "cine_nido/mis_compras.html", {"compras": demo.COMPRAS})


# ---------------------------- Panel interno ----------------------------

def _panel(seccion_activa, extra=None):
    ctx = {"seccion_activa": seccion_activa, "secciones": demo.PANEL_SECCIONES}
    ctx.update(extra or {})
    return ctx


def panel_dashboard(request):
    return render(request, "cine_nido/panel/dashboard.html", _panel("dashboard", {
        "proximas": [dict(f, pelicula=demo.obtener_pelicula(f["pelicula_id"])["nombre"]) for f in demo.FUNCIONES[:5]],
    }))


def panel_listado(request, seccion):
    datos = demo.PANEL_SECCIONES.get(seccion)
    if not datos:
        raise Http404("Sección no encontrada")
    return render(request, "cine_nido/panel/listado.html", _panel(seccion, {"datos": datos}))


def panel_validar(request):
    return render(request, "cine_nido/panel/validar.html", _panel("validar"))
