from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models


class UserManager(BaseUserManager):
    """Manager that creates users with a normalized email address."""

    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("El correo electrónico es obligatorio.")

        email = self.normalize_email(email).strip().lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Un superusuario debe tener is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Un superusuario debe tener is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField("correo electrónico", max_length=100, unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email


class Sala(models.Model):
    nombre_sala = models.CharField(max_length=50)

    def __str__(self):
        return self.nombre_sala


class Asiento(models.Model):
    sala = models.ForeignKey(Sala, on_delete=models.CASCADE, related_name="asientos")
    fila = models.CharField(max_length=5)
    numero = models.IntegerField()

    def __str__(self):
        return f"{self.sala} - {self.fila}{self.numero}"


class Pelicula(models.Model):
    nombre = models.CharField(max_length=150)
    portada = models.URLField(max_length=500, blank=True, null=True)
    fecha_estreno = models.DateField()
    duracion = models.IntegerField()
    clasificacion = models.CharField(max_length=30)
    director = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


class Funcion(models.Model):
    sala = models.ForeignKey(Sala, on_delete=models.PROTECT, related_name="funciones")
    pelicula = models.ForeignKey(Pelicula, on_delete=models.CASCADE, related_name="funciones")
    horario = models.DateField()
    hora = models.DateTimeField()

    def __str__(self):
        return f"{self.pelicula} - {self.hora}"


class ProductoConfiteria(models.Model):
    nombre = models.CharField(max_length=100)
    foto = models.URLField(max_length=500, blank=True, null=True)
    precio_unitario = models.IntegerField()

    def __str__(self):
        return self.nombre


class Usuario(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perfil",
    )
    nombre_completo = models.CharField(max_length=100)
    email = models.EmailField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre_completo


class Compra(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="compras")
    fecha_compra = models.DateTimeField(auto_now_add=True)
    total = models.IntegerField()

    def __str__(self):
        return f"Compra {self.pk} - {self.usuario}"


class Entrada(models.Model):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name="entradas")
    funcion = models.ForeignKey(Funcion, on_delete=models.PROTECT, related_name="entradas")
    asiento = models.ForeignKey(Asiento, on_delete=models.PROTECT, related_name="entradas")
    precio = models.IntegerField()

    def __str__(self):
        return f"Entrada {self.pk} - {self.funcion}"


class DetalleConfiteria(models.Model):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name="detalles_confiteria")
    producto_confiteria = models.ForeignKey(
        ProductoConfiteria,
        on_delete=models.PROTECT,
        related_name="detalles_compra",
    )
    cantidad = models.IntegerField(default=1)
    precio_unitario = models.IntegerField()

    def __str__(self):
        return f"{self.producto_confiteria} x {self.cantidad}"
