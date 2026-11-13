from django.db import models
from django.conf import settings
from django.utils import timezone


class Sala(models.Model):
    nombre_sala = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre_sala

    @property
    def nombre(self):
        return self.nombre_sala

    @property
    def filas(self):
        total = self.asientos.values("fila").distinct().count()
        return total or 8

    @property
    def por_fila(self):
        max_num = self.asientos.aggregate(models.Max("numero"))["numero__max"]
        return max_num or 12

    @property
    def capacidad(self):
        total = self.asientos.count()
        return total if total else self.filas * self.por_fila

    @property
    def accesibles(self):
        return min(4, self.por_fila)

    @property
    def pasillo(self):
        return self.por_fila // 2

    @property
    def estado(self):
        return "activa"


class Asiento(models.Model):
    sala = models.ForeignKey(Sala, on_delete=models.CASCADE, related_name="asientos")
    fila = models.CharField(max_length=5)
    numero = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["sala", "fila", "numero"], name="asiento_unico_por_sala")
        ]
        ordering = ["sala", "fila", "numero"]

    def __str__(self):
        return f"{self.sala} - {self.fila}{self.numero}"

    @property
    def codigo(self):
        return f"{self.fila}{self.numero}"


class Pelicula(models.Model):
    nombre = models.CharField(max_length=150)
    portada = models.URLField(max_length=500, blank=True, null=True)
    sinopsis = models.TextField(blank=True)
    fecha_estreno = models.DateField()
    duracion = models.PositiveIntegerField(help_text="Duración en minutos")
    clasificacion = models.CharField(max_length=30)
    director = models.CharField(max_length=100)
    activa = models.BooleanField(default=True) 

    def __str__(self):
        return self.nombre

    @property
    def estado(self):
        if not self.activa:
            return "fuera"
        if self.fecha_estreno and self.fecha_estreno > timezone.localdate():
            return "proximo"
        return "en_cartelera"

    @property
    def genero(self):
        return self.director or "Cine"

    @property
    def formato(self):
        return "2D"

    @property
    def idioma(self):
        return "Subtitulada"

    @property
    def trailer(self):
        return "#"


class Funcion(models.Model):
    sala = models.ForeignKey(Sala, on_delete=models.PROTECT, related_name="funciones")
    pelicula = models.ForeignKey(Pelicula, on_delete=models.PROTECT, related_name="funciones")
    fecha_hora = models.DateTimeField()   # reemplaza horario (date) + hora (datetime)
    precio = models.PositiveIntegerField()

    class Meta:
        ordering = ["fecha_hora"]
        constraints = [
            models.UniqueConstraint(fields=["sala", "fecha_hora"], name="funcion_unica_por_sala_y_hora")
        ]

    def __str__(self):
        return f"{self.pelicula} - {self.sala} - {self.fecha_hora:%d/%m/%Y %H:%M}"

    @property
    def fecha(self):
        dt = timezone.localtime(self.fecha_hora) if timezone.is_aware(self.fecha_hora) else self.fecha_hora
        return dt.date()

    @property
    def hora(self):
        dt = timezone.localtime(self.fecha_hora) if timezone.is_aware(self.fecha_hora) else self.fecha_hora
        return dt.strftime("%H:%M")

    @property
    def formato(self):
        return "2D"

    @property
    def idioma(self):
        return "Subtitulada"


class ProductoConfiteria(models.Model):
    nombre = models.CharField(max_length=100)
    foto = models.URLField(max_length=500, blank=True, null=True)
    precio_unitario = models.PositiveIntegerField()
    disponible = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

    @property
    def precio(self):
        return self.precio_unitario

    @property
    def categoria(self):
        n = (self.nombre or "").lower()
        if "combo" in n:
            return "Combos"
        if "cabrita" in n or "pop" in n or "palomita" in n:
            return "Cabritas"
        if "bebida" in n or "agua" in n or "jugo" in n or "lata" in n or "ml" in n:
            return "Bebidas"
        return "Dulces"

    @property
    def emoji(self):
        cat = self.categoria
        if cat in ("Combos", "Cabritas"):
            return "🍿"
        if cat == "Bebidas":
            return "🥤"
        return "🍫"

    @property
    def detalle(self):
        return "Disponible en confitería"


class Compra(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="compras")
    fecha_compra = models.DateTimeField(auto_now_add=True)
    total = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-fecha_compra"]

    def __str__(self):
        return f"Compra #{self.pk} - {self.usuario}"

    @property
    def numero(self):
        return f"CN-{self.pk:06d}" if self.pk else "CN-000000"

    @property
    def fecha(self):
        return self.fecha_compra

    @property
    def estado(self):
        return {"texto": "Pagada", "badge": "ok"}

    @property
    def canal(self):
        return "Online"

    @property
    def pelicula(self):
        primera = self.entradas.select_related("funcion__pelicula").first()
        return primera.funcion.pelicula.nombre if primera else "Confitería"

    @property
    def funcion(self):
        primera = self.entradas.select_related("funcion__sala").first()
        if not primera:
            return "—"
        return f"{primera.funcion.sala.nombre_sala} · {primera.funcion.hora}"

    @property
    def sala_nombre(self):
        primera = self.entradas.select_related("funcion__sala").first()
        return primera.funcion.sala.nombre_sala if primera else "—"

    @property
    def hora_funcion(self):
        primera = self.entradas.select_related("funcion").first()
        return primera.funcion.hora if primera else "—"

    @property
    def fecha_funcion(self):
        primera = self.entradas.select_related("funcion").first()
        return primera.funcion.fecha if primera else self.fecha_compra.date()

    @property
    def asientos(self):
        codigos = [
            f"{e.asiento.fila}{e.asiento.numero}"
            for e in self.entradas.select_related("asiento").order_by("asiento__fila", "asiento__numero")
        ]
        return ", ".join(codigos) if codigos else "—"

    @property
    def correo(self):
        return self.usuario.email or self.usuario.username

    @property
    def items(self):
        resultado = []
        entradas_qs = list(self.entradas.select_related("asiento", "funcion__pelicula"))
        if entradas_qs:
            por_precio = {}
            for e in entradas_qs:
                por_precio.setdefault(e.precio, []).append(e)
            for precio, lista in por_precio.items():
                cantidad = len(lista)
                resultado.append({
                    "nombre": f"Entrada ({lista[0].funcion.pelicula.nombre})",
                    "cantidad": cantidad,
                    "precio": precio,
                    "subtotal": cantidad * precio,
                })
        for d in self.detalles_confiteria.select_related("producto_confiteria"):
            resultado.append({
                "nombre": d.producto_confiteria.nombre,
                "cantidad": d.cantidad,
                "precio": d.precio_unitario,
                "subtotal": d.cantidad * d.precio_unitario,
            })
        return resultado


class Entrada(models.Model):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name="entradas")
    funcion = models.ForeignKey(Funcion, on_delete=models.PROTECT, related_name="entradas")
    asiento = models.ForeignKey(Asiento, on_delete=models.PROTECT)
    precio = models.PositiveIntegerField() 

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["funcion", "asiento"], name="asiento_unico_por_funcion")
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.asiento_id and self.funcion_id and self.asiento.sala_id != self.funcion.sala_id:
            raise ValidationError("El asiento no pertenece a la sala de la función.")


class DetalleConfiteria(models.Model):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name="detalles_confiteria")
    producto_confiteria = models.ForeignKey(ProductoConfiteria, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.PositiveIntegerField()

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario
