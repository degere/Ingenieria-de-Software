from django.db import models
from django.conf import settings

class Sala(models.Model):
    nombre_sala = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre_sala

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


class ProductoConfiteria(models.Model):
    nombre = models.CharField(max_length=100)
    foto = models.URLField(max_length=500, blank=True, null=True)
    precio_unitario = models.PositiveIntegerField()
    disponible = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


class Compra(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="compras")
    fecha_compra = models.DateTimeField(auto_now_add=True)
    total = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-fecha_compra"]

    def __str__(self):
        return f"Compra #{self.pk} - {self.usuario}"


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
        if self.asiento.sala_id != self.funcion.sala_id:
            raise ValidationError("El asiento no pertenece a la sala de la función.")


class DetalleConfiteria(models.Model):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name="detalles_confiteria")
    producto_confiteria = models.ForeignKey(ProductoConfiteria, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.PositiveIntegerField() 