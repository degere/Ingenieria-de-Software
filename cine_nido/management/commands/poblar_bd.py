from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from cine_nido import datos_demo as demo
from cine_nido.models import Asiento, Funcion, Pelicula, ProductoConfiteria, Sala


class Command(BaseCommand):
    help = "Puebla la base de datos con salas, asientos, películas, funciones y productos iniciales."

    def handle(self, *args, **options):
        hoy = timezone.localdate()

        # 1. Salas y asientos
        salas_objs = {}
        for s in demo.SALAS:
            sala, _ = Sala.objects.get_or_create(nombre_sala=s["nombre"])
            salas_objs[s["nombre"]] = sala
            if not sala.asientos.exists():
                asientos = []
                for i in range(s.get("filas", 8)):
                    letra = chr(ord("A") + i)
                    for n in range(1, s.get("por_fila", 12) + 1):
                        asientos.append(Asiento(sala=sala, fila=letra, numero=n))
                Asiento.objects.bulk_create(asientos, ignore_conflicts=True)

        # 2. Películas
        peliculas_objs = {}
        for p in demo.PELICULAS:
            pelicula, _ = Pelicula.objects.update_or_create(
                nombre=p["nombre"],
                defaults={
                    "portada": p["portada"],
                    "sinopsis": p["sinopsis"],
                    "fecha_estreno": p["fecha_estreno"],
                    "duracion": p["duracion"],
                    "clasificacion": p["clasificacion"],
                    "director": p["director"],
                    "activa": p["estado"] != "fuera",
                },
            )
            peliculas_objs[p["id"]] = pelicula

        # 3. Funciones
        for f in demo.FUNCIONES:
            pelicula = peliculas_objs.get(f["pelicula_id"])
            sala = salas_objs.get(f["sala"])
            if not pelicula or not sala:
                continue
            partes_hora = [int(x) for x in f["hora"].split(":")]
            dt = datetime.combine(f["fecha"], time(partes_hora[0], partes_hora[1]))
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.get_current_timezone())
            Funcion.objects.get_or_create(
                sala=sala,
                fecha_hora=dt,
                defaults={
                    "pelicula": pelicula,
                    "precio": f["precio"],
                },
            )

        # 4. Productos de confitería
        for prod in demo.PRODUCTOS:
            ProductoConfiteria.objects.update_or_create(
                nombre=prod["nombre"],
                defaults={
                    "precio_unitario": prod["precio"],
                    "disponible": True,
                },
            )

        self.stdout.write(self.style.SUCCESS("Base de datos poblada correctamente."))
