from django.contrib import admin
from .models import (
    Sala,
    Asiento,
    Pelicula,
    Funcion,
    ProductoConfiteria,
    Compra,
    Entrada,
    DetalleConfiteria,
)


class AsientoInline(admin.TabularInline):
    model = Asiento
    extra = 0


@admin.register(Sala)
class SalaAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre_sala", "capacidad")
    search_fields = ("nombre_sala",)
    inlines = [AsientoInline]


@admin.register(Asiento)
class AsientoAdmin(admin.ModelAdmin):
    list_display = ("id", "sala", "fila", "numero")
    list_filter = ("sala", "fila")
    search_fields = ("sala__nombre_sala", "fila")


@admin.register(Pelicula)
class PeliculaAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "director", "clasificacion", "duracion", "fecha_estreno", "activa")
    list_filter = ("activa", "clasificacion", "fecha_estreno")
    search_fields = ("nombre", "director", "sinopsis")


@admin.register(Funcion)
class FuncionAdmin(admin.ModelAdmin):
    list_display = ("id", "pelicula", "sala", "fecha_hora", "precio")
    list_filter = ("sala", "pelicula", "fecha_hora")
    search_fields = ("pelicula__nombre", "sala__nombre_sala")


@admin.register(ProductoConfiteria)
class ProductoConfiteriaAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "precio_unitario", "disponible")
    list_filter = ("disponible",)
    search_fields = ("nombre",)


class EntradaInline(admin.TabularInline):
    model = Entrada
    extra = 0


class DetalleConfiteriaInline(admin.TabularInline):
    model = DetalleConfiteria
    extra = 0


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ("id", "numero", "usuario", "fecha_compra", "total")
    list_filter = ("fecha_compra",)
    search_fields = ("usuario__username", "usuario__email")
    inlines = [EntradaInline, DetalleConfiteriaInline]


@admin.register(Entrada)
class EntradaAdmin(admin.ModelAdmin):
    list_display = ("id", "compra", "funcion", "asiento", "precio")
    list_filter = ("funcion__sala", "funcion__pelicula")


@admin.register(DetalleConfiteria)
class DetalleConfiteriaAdmin(admin.ModelAdmin):
    list_display = ("id", "compra", "producto_confiteria", "cantidad", "precio_unitario")
    list_filter = ("producto_confiteria",)
