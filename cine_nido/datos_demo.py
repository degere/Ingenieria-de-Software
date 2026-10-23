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

GENEROS = ["Acción", "Animación", "Aventura", "Ciencia ficción", "Comedia", "Drama", "Romance", "Suspenso", "Terror"]
CLASIFICACIONES = ["TE", "+7", "+10", "+14", "+18"]
IDIOMAS = ["Doblada", "Subtitulada"]
FORMATOS = ["2D", "3D"]
ESTADOS_PELICULA = [("proximo", "Próximo estreno"), ("en_cartelera", "En cartelera"), ("fuera", "Fuera de cartelera")]
CATEGORIAS = ["Combos", "Cabritas", "Bebidas", "Dulces"]
TIPOS_CUENTA = ["Cliente", "Administrador"]

SALAS = [
    {"id": 1, "nombre": "Sala 1", "filas": 8, "por_fila": 12, "accesibles": 4, "pasillo": 6, "estado": "activa"},
    {"id": 2, "nombre": "Sala 2", "filas": 8, "por_fila": 12, "accesibles": 4, "pasillo": 6, "estado": "activa"},
]

USUARIOS = [
    {"id": 1, "nombre": "Ana Pérez", "rut": "15.432.876-1", "telefono": "+56 9 8765 4321", "correo": "ana@correo.cl", "tipo_cuenta": "Cliente", "activo": True},
    {"id": 2, "nombre": "José Sosa", "rut": "12.345.678-9", "telefono": "+56 9 1234 5678", "correo": "jose@cinenido.cl", "tipo_cuenta": "Administrador", "activo": True},
]

CAJAS = [
    {"id": 1, "turno": "Ayer tarde", "usuario": "Luis Soto", "punto": "Boletería", "inicial": 30000, "efectivo": 120500, "tarjeta": 95000, "contado": 150500},
    {"id": 2, "turno": "Ayer noche", "usuario": "Marta Díaz", "punto": "Confitería", "inicial": 20000, "efectivo": 54300, "tarjeta": 44000, "contado": 72800},
]

DETALLE_COMPRAS = {
    123: {"funcion": "Sala 1 · 20:30", "asientos": "D5, D6", "items": [("Entrada general", 2, 5500), ("Combo Nido (2 personas)", 1, 9900)], "correo": "ana@correo.cl"},
    118: {"funcion": "Sala 2 · 18:00", "asientos": "F3, F4", "items": [("Entrada estudiante", 2, 4500)], "correo": "—"},
    101: {"funcion": "Sala 1 · 15:30", "asientos": "C7, C8", "items": [("Entrada general", 2, 5500)], "correo": "pedro@correo.cl", "motivo_anulacion": "Cliente no podía asistir"},
}

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
        "filas": [[s["nombre"], s["filas"] * s["por_fila"], s["filas"], s["accesibles"], {"texto": "Activa", "badge": "ok"}] for s in SALAS]},
    "productos": {"titulo": "Productos de confitería", "nuevo": "Nuevo producto",
        "columnas": ["Producto", "Categoría", "Precio", "Stock"],
        "filas": [[p["nombre"], p["categoria"], _clp(p["precio"]), {"texto": str(8 + p["id"] * 5), "badge": "aviso"} if p["id"] in (3, 6) else str(8 + p["id"] * 5)] for p in PRODUCTOS]},
    "ventas": {"titulo": "Ventas", "nuevo": None,
        "columnas": ["N° venta", "Fecha", "Película", "Canal", "Total", "Estado"],
        "filas": [[c["numero"], c["fecha"].strftime("%d/%m/%Y"), c["pelicula"], c["canal"], _clp(c["total"]), c["estado"]] for c in COMPRAS]},
    "usuarios": {"titulo": "Usuarios", "nuevo": "Nuevo usuario",
        "columnas": ["Nombre", "Correo", "Tipo de cuenta", "Estado"],
        "filas": [[u["nombre"], u["correo"], u["tipo_cuenta"], {"texto": "Activo", "badge": "ok"}] for u in USUARIOS]},
    "caja": {"titulo": "Caja (apertura y cierre)", "nuevo": "Abrir caja",
        "columnas": ["Turno", "Responsable", "Monto inicial", "Ventas", "Diferencia"],
        "filas": [[c["turno"], c["usuario"], _clp(c["inicial"]), _clp(c["efectivo"] + c["tarjeta"]),
                   {"texto": _clp(c["contado"] - c["inicial"] - c["efectivo"]).replace("$-", "-$"), "badge": "ok" if c["contado"] == c["inicial"] + c["efectivo"] else "error"}] for c in CAJAS]},
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


SECCIONES_CON_FORMULARIO = ["peliculas", "funciones", "salas", "productos", "usuarios", "caja"]


def obtener_registro(seccion, pk):
    fuentes = {"peliculas": PELICULAS, "funciones": FUNCIONES, "salas": SALAS, "productos": PRODUCTOS,
               "usuarios": USUARIOS, "caja": CAJAS}
    lista = fuentes.get(seccion, [])
    return lista[pk - 1] if 0 < pk <= len(lista) else None


def obtener_compra(pk):
    if not 0 < pk <= len(COMPRAS):
        return None
    compra = dict(COMPRAS[pk - 1])
    compra.update(DETALLE_COMPRAS.get(compra["id"], {}))
    compra["items"] = [{"nombre": n, "cantidad": c, "precio": p, "subtotal": c * p} for n, c, p in compra.get("items", [])]
    return compra
