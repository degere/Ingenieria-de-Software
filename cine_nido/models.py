from django.db import models
from django.conf import settings

class Sala(models.Model):
    nombre_sala = models.CharField(max_length=50)

class Asiento(models.Model):
    sala = models.ForeignKey(Sala, on_delete=models.CASCADE)
    fila = models.CharField(max_length=5)
    numero = models.IntegerField()

class Pelicula(models.Model):
    nombre = models.CharField(max_length=150)
    portada = models.URLField(max_length=500, blank=True, null=True)
    fecha_estreno = models.DateField()
    duracion = models.IntegerField()
    clasificacion = models.CharField(max_length=30)
    director = models.CharField(max_length=100)

class Funcion(models.Model):
    sala = models.ForeignKey(Sala, on_delete=models.PROTECT)
    pelicula = models.ForeignKey(Pelicula, on_delete=models.CASCADE)
    horario = models.DateField()
    hora = models.DateTimeField()

class ProductoConfiteria(models.Model):
    nombre = models.CharField(max_length=100)
    foto = models.URLField(max_length=500, blank=True, null=True)
    precio_unitario = models.IntegerField()

class Usuario(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nombre_completo = models.CharField(max_length=100)
    contraseña = models.CharField(max_length=100)
    email= models.EmailField(max_length=100)

class Compra(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    fecha_compra = models.DateTimeField(auto_now_add=True)
    total = models.IntegerField()

class Entrada(models.Model):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE)
    funcion = models.ForeignKey(Funcion, on_delete=models.PROTECT)
    asiento = models.ForeignKey(Asiento, on_delete=models.PROTECT)
    precio = models.IntegerField()

class DetalleConfiteria(models.Model):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE)
    producto_confiteria = models.ForeignKey(ProductoConfiteria, on_delete=models.PROTECT)
    cantidad = models.IntegerField(default=1)
    precio_unitario = models.IntegerField()