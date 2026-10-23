"""
DATOS DE DEMOSTRACIÓN (TEMPORAL)
--------------------------------
Solo sirven para que el frontend se vea con contenido mientras el backend no
está listo. Cuando existan las consultas reales (modelos de models.py), cada
función de views.py debe dejar de usar este archivo y este archivo se borra.

Algunos campos (sinopsis, genero, idioma, formato, estado, trailer) salen del
informe (R7) y todavía NO existen en models.py.
"""
from datetime import date, timedelta

HOY = date.today()


def _clp(n):
    """Formato chileno: 9900 -> $9.900"""
    return "$" + format(n, ",").replace(",", ".")


PELICULAS = [
    {"id": 1, "nombre": "Noche en el Muelle", "genero": "Drama", "duracion": 118, "clasificacion": "+14", "idioma": "Subtitulada", "formato": "2D", "director": "Camila Fuentes", "estado": "en_cartelera", "fecha_estreno": HOY - timedelta(days=10), "portada": None, "trailer": "#",
     "sinopsis": "Una pescadora regresa a su pueblo del sur y descubre un secreto que cambiará la vida de toda la comunidad."},
    {"id": 2, "nombre": "El Faro de Cristal", "genero": "Aventura", "duracion": 104, "clasificacion": "TE", "idioma": "Doblada", "formato": "3D", "director": "Tomás Riquelme", "estado": "en_cartelera", "fecha_estreno": HOY - timedelta(days=3), "portada": None, "trailer": "#",
     "sinopsis": "Tres amigos viajan hasta un faro misterioso donde cada luz cuenta una historia distinta."},
    {"id": 3, "nombre": "Risas a Medianoche", "genero": "Comedia", "duracion": 96, "clasificacion": "+7", "idioma": "Subtitulada", "formato": "2D", "director": "Paula Navarro", "estado": "en_cartelera", "fecha_estreno": HOY - timedelta(days=17), "portada": None, "trailer": "#",
     "sinopsis": "Un cómico fracasado tiene una sola noche para salvar el teatro de su barrio."},
    {"id": 4, "nombre": "Sombras del Bosque", "genero": "Terror", "duracion": 101, "clasificacion": "+18", "idioma": "Doblada", "formato": "2D", "director": "Iván Salas", "estado": "en_cartelera", "fecha_estreno": HOY - timedelta(days=6), "portada": None, "trailer": "#",
     "sinopsis": "Un grupo de excursionistas se pierde en un bosque donde algo los observa."},
    {"id": 5, "nombre": "Pequeños Gigantes", "genero": "Animación", "duracion": 92, "clasificacion": "TE", "idioma": "Doblada", "formato": "3D", "director": "Marta Oyarzún", "estado": "en_cartelera", "fecha_estreno": HOY - timedelta(days=1), "portada": None, "trailer": "#",
     "sinopsis": "Un grupo de animales diminutos se une para proteger su hogar de una gran tormenta."},
    {"id": 6, "nombre": "Código Rojo", "genero": "Acción", "duracion": 123, "clasificacion": "+14", "idioma": "Subtitulada", "formato": "2D", "director": "Diego Paredes", "estado": "en_cartelera", "fecha_estreno": HOY - timedelta(days=12), "portada": None, "trailer": "#",
     "sinopsis": "Una agente retirada vuelve al servicio para detener un atentado en la capital."},
    {"id": 7, "nombre": "Lluvia de Verano", "genero": "Romance", "duracion": 109, "clasificacion": "+7", "idioma": "Subtitulada", "formato": "2D", "director": "Elena Vidal", "estado": "proximo", "fecha_estreno": HOY + timedelta(days=9), "portada": None, "trailer": "#",
     "sinopsis": "Dos desconocidos se encuentran cada tarde bajo el mismo paradero durante un verano lluvioso."},
    {"id": 8, "nombre": "Estrella Perdida", "genero": "Ciencia ficción", "duracion": 131, "clasificacion": "+10", "idioma": "Doblada", "formato": "3D", "director": "Andrés Molina", "estado": "proximo", "fecha_estreno": HOY + timedelta(days=16), "portada": None, "trailer": "#",
     "sinopsis": "La tripulación de una nave a la deriva debe decidir si regresa a casa o sigue una señal desconocida."},
    {"id": 9, "nombre": "La Casa del Lago", "genero": "Suspenso", "duracion": 112, "clasificacion": "+14", "idioma": "Subtitulada", "formato": "2D", "director": "Sofía Castillo", "estado": "proximo", "fecha_estreno": HOY + timedelta(days=23), "portada": None, "trailer": "#",
     "sinopsis": "Una familia hereda una casa junto a un lago y empieza a notar cosas que no cuadran."},
]

HORAS = ["15:30", "18:00", "20:30"]
PRECIOS = {"general": 5500, "estudiante": 4500, "adulto_mayor": 4000}  # lista de precios (sección 3.3 del informe)

FUNCIONES = []
_id = 1
for _p in PELICULAS:
    if _p["estado"] != "en_cartelera":
        continue
    for _d in range(4):
        for _i, _h in enumerate(HORAS):
            if (_p["id"] + _d + _i) % 2 == 0:  # reparte horarios para que no todas tengan lo mismo
                FUNCIONES.append({"id": _id, "pelicula_id": _p["id"], "sala": "Sala %d" % (1 + (_i % 2)), "fecha": HOY + timedelta(days=_d), "hora": _h, "formato": _p["formato"], "idioma": _p["idioma"], "precio": PRECIOS["general"]})
                _id += 1

PRODUCTOS = [
    {"id": 1, "nombre": "Combo Nido (2 personas)", "categoria": "Combos", "precio": 9900, "emoji": "🍿", "detalle": "Cabritas grandes + 2 bebidas medianas"},
    {"id": 2, "nombre": "Combo Individual", "categoria": "Combos", "precio": 5500, "emoji": "🥤", "detalle": "Cabritas medianas + 1 bebida"},
    {"id": 3, "nombre": "Cabritas grandes", "categoria": "Cabritas", "precio": 4500, "emoji": "🍿", "detalle": "Saladas o acarameladas"},
    {"id": 4, "nombre": "Cabritas medianas", "categoria": "Cabritas", "precio": 3500, "emoji": "🍿", "detalle": "Saladas o acarameladas"},
    {"id": 5, "nombre": "Bebida 500 ml", "categoria": "Bebidas", "precio": 2500, "emoji": "🥤", "detalle": "Variedad a elección"},
    {"id": 6, "nombre": "Agua mineral", "categoria": "Bebidas", "precio": 1800, "emoji": "💧", "detalle": "Con o sin gas"},
    {"id": 7, "nombre": "Chocolate", "categoria": "Dulces", "precio": 1500, "emoji": "🍫", "detalle": "Barra 40 g"},
    {"id": 8, "nombre": "Gomitas", "categoria": "Dulces", "precio": 1800, "emoji": "🍬", "detalle": "Bolsa 80 g"},
]

COMPRAS = [
    {"id": 123, "numero": "CN-000123", "fecha": HOY - timedelta(days=2), "pelicula": "Noche en el Muelle", "total": 20900, "estado": {"texto": "Pagada", "badge": "ok"}, "canal": "Online"},
    {"id": 118, "numero": "CN-000118", "fecha": HOY - timedelta(days=15), "pelicula": "Risas a Medianoche", "total": 9000, "estado": {"texto": "Pagada", "badge": "ok"}, "canal": "Boletería"},
    {"id": 101, "numero": "CN-000101", "fecha": HOY - timedelta(days=40), "pelicula": "Código Rojo", "total": 11000, "estado": {"texto": "Anulada", "badge": "error"}, "canal": "Online"},
]

PANEL_SECCIONES = {
    "peliculas": {"titulo": "Películas", "nuevo": "Nueva película",
        "columnas": ["Título", "Género", "Duración", "Clasificación", "Estado"],
        "filas": [[p["nombre"], p["genero"], "%d min" % p["duracion"], p["clasificacion"],
                   {"texto": "En cartelera", "badge": "ok"} if p["estado"] == "en_cartelera" else {"texto": "Próximo estreno", "badge": "info"}] for p in PELICULAS]},
    "funciones": {"titulo": "Funciones", "nuevo": "Nueva función",
        "columnas": ["Película", "Sala", "Fecha", "Hora", "Vendidas"],
        "filas": [[next(p["nombre"] for p in PELICULAS if p["id"] == f["pelicula_id"]), f["sala"], f["fecha"].strftime("%d/%m/%Y"), f["hora"], "%d / 96" % ((f["id"] * 7) % 96)] for f in FUNCIONES[:12]]},
    "salas": {"titulo": "Salas", "nuevo": "Nueva sala",
        "columnas": ["Sala", "Capacidad", "Filas", "Asientos accesibles", "Estado"],
        "filas": [["Sala 1", 96, 8, 4, {"texto": "Activa", "badge": "ok"}], ["Sala 2", 96, 8, 4, {"texto": "Activa", "badge": "ok"}]]},
    "productos": {"titulo": "Productos de confitería", "nuevo": "Nuevo producto",
        "columnas": ["Producto", "Categoría", "Precio", "Stock"],
        "filas": [[p["nombre"], p["categoria"], _clp(p["precio"]), {"texto": str(8 + p["id"] * 5), "badge": "aviso"} if p["id"] in (3, 6) else str(8 + p["id"] * 5)] for p in PRODUCTOS]},
    "ventas": {"titulo": "Ventas", "nuevo": None,
        "columnas": ["N° venta", "Fecha", "Película", "Canal", "Total", "Estado"],
        "filas": [[c["numero"], c["fecha"].strftime("%d/%m/%Y"), c["pelicula"], c["canal"], _clp(c["total"]), c["estado"]] for c in COMPRAS]},
    "usuarios": {"titulo": "Usuarios", "nuevo": "Nuevo usuario",
        "columnas": ["Nombre", "Correo", "Rol", "Estado"],
        "filas": [["Ana Pérez", "ana@correo.cl", "Cliente", {"texto": "Activo", "badge": "ok"}], ["Luis Soto", "luis@cinenido.cl", "Vendedor", {"texto": "Activo", "badge": "ok"}],
                  ["Marta Díaz", "marta@cinenido.cl", "Encargada de confitería", {"texto": "Activo", "badge": "ok"}], ["José Sosa", "jose@cinenido.cl", "Administrador", {"texto": "Activo", "badge": "ok"}]]},
    "caja": {"titulo": "Caja (apertura y cierre)", "nuevo": "Abrir caja",
        "columnas": ["Turno", "Usuario", "Monto inicial", "Ventas", "Diferencia"],
        "filas": [["Ayer tarde", "Luis Soto", "$30.000", "$215.500", {"texto": "$0", "badge": "ok"}], ["Ayer noche", "Marta Díaz", "$20.000", "$98.300", {"texto": "-$1.500", "badge": "error"}]]},
    "reportes": {"titulo": "Reportes", "nuevo": None,
        "columnas": ["Reporte", "Período", "Formato"],
        "filas": [["Ventas de entradas", "Último mes", "PDF / Excel"], ["Ventas de confitería", "Último mes", "PDF / Excel"], ["Ocupación por sala", "Última semana", "PDF / Excel"]]},
}


def obtener_pelicula(pk):
    return next((p for p in PELICULAS if p["id"] == pk), None)


def obtener_funcion(pk):
    return next((f for f in FUNCIONES if f["id"] == pk), None)


def funciones_por_dia(pelicula_id):
    dias = {}
    for f in FUNCIONES:
        if f["pelicula_id"] == pelicula_id:
            dias.setdefault(f["fecha"], []).append(f)
    return [{"fecha": d, "funciones": dias[d]} for d in sorted(dias)]


def productos_por_categoria():
    orden = ["Combos", "Cabritas", "Bebidas", "Dulces"]
    return [{"nombre": c, "slug": c.lower(), "productos": [p for p in PRODUCTOS if p["categoria"] == c]} for c in orden]


def mapa_sala(funcion_id):
    """Sala de 8 filas x 12 asientos. Los estados se reparten de forma fija para la demo."""
    filas = []
    for fi, letra in enumerate("ABCDEFGH"):
        asientos = []
        for n in range(1, 13):
            estado = "disponible"
            if (fi * 7 + n * 3 + funcion_id) % 5 == 0:
                estado = "ocupado"
            elif (fi * 5 + n * 2 + funcion_id) % 13 == 0:
                estado = "reservado"
            if letra == "H" and n in (1, 2, 11, 12):
                estado = "movilidad"
            asientos.append({"codigo": "%s%d" % (letra, n), "numero": n, "estado": estado, "pasillo": n == 6})
        filas.append({"letra": letra, "asientos": asientos})
    return filas
