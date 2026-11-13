import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    Asiento,
    Compra,
    DetalleConfiteria,
    Entrada,
    Funcion,
    Pelicula,
    ProductoConfiteria,
    Sala,
)


class AutenticacionTests(TestCase):
    def test_registro_crea_usuario_django_y_inicia_sesion(self):
        response = self.client.post(reverse("registro"), {
            "nombre": "Ana Pérez",
            "correo": "ana@example.com",
            "clave": "T7!rK9#vQ2mL",
            "clave2": "T7!rK9#vQ2mL",
        })

        usuario = get_user_model().objects.get(email="ana@example.com")
        self.assertEqual(usuario.username, "ana@example.com")
        self.assertEqual(usuario.first_name, "Ana")
        self.assertEqual(usuario.last_name, "Pérez")
        self.assertTrue(usuario.check_password("T7!rK9#vQ2mL"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), usuario.pk)
        self.assertRedirects(response, reverse("cartelera"))

    def test_login_acepta_correo_y_cierra_sesion_desde_el_sitio(self):
        usuario = get_user_model().objects.create_user(
            username="ana",
            email="ana@example.com",
            password="T7!rK9#vQ2mL",
        )

        response = self.client.post(reverse("ingresar"), {
            "correo": "ANA@example.com",
            "clave": "T7!rK9#vQ2mL",
        })

        self.assertRedirects(response, reverse("cartelera"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), usuario.pk)
        response = self.client.post(reverse("salir"))
        self.assertRedirects(response, reverse("cartelera"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_registro_rechaza_correo_existente_y_claves_distintas(self):
        get_user_model().objects.create_user(
            username="ana",
            email="ana@example.com",
            password="T7!rK9#vQ2mL",
        )

        response = self.client.post(reverse("registro"), {
            "nombre": "Ana Pérez",
            "correo": "ANA@example.com",
            "clave": "T7!rK9#vQ2mL",
            "clave2": "Otra-clave-123!",
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertNotIn("_auth_user_id", self.client.session)


class FlujoWebYPanelTests(TestCase):
    def setUp(self):
        self.hoy = timezone.localdate()
        self.sala = Sala.objects.create(nombre_sala="Sala 1")
        for letra in ("A", "B"):
            for num in (1, 2, 3, 4):
                Asiento.objects.create(sala=self.sala, fila=letra, numero=num)

        self.pelicula = Pelicula.objects.create(
            nombre="Noche en el Muelle",
            sinopsis="Drama en el sur.",
            fecha_estreno=self.hoy - timedelta(days=5),
            duracion=118,
            clasificacion="+14",
            director="Camila Fuentes",
            activa=True,
        )
        self.pelicula_proxima = Pelicula.objects.create(
            nombre="Lluvia de Verano",
            sinopsis="Próximo estreno.",
            fecha_estreno=self.hoy + timedelta(days=10),
            duracion=105,
            clasificacion="+7",
            director="Elena Vidal",
            activa=True,
        )
        self.funcion = Funcion.objects.create(
            sala=self.sala,
            pelicula=self.pelicula,
            fecha_hora=timezone.now() + timedelta(days=1),
            precio=5500,
        )
        self.producto = ProductoConfiteria.objects.create(
            nombre="Combo Nido (2 personas)",
            precio_unitario=9900,
            disponible=True,
        )

    def test_cartelera_y_detalle_muestran_datos_bd(self):
        res = self.client.get(reverse("cartelera"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Noche en el Muelle")
        self.assertContains(res, "Lluvia de Verano")

        res_det = self.client.get(reverse("pelicula_detalle", args=[self.pelicula.id]))
        self.assertEqual(res_det.status_code, 200)
        self.assertContains(res_det, "Noche en el Muelle")
        self.assertContains(res_det, "Sala 1")

    def test_flujo_completo_de_compra_invitado_pide_correo_y_reserva_asiento(self):
        from django.test import Client

        # 1. Ver mapa de asientos
        res_asientos = self.client.get(reverse("asientos", args=[self.funcion.id]))
        self.assertEqual(res_asientos.status_code, 200)

        # 2. Seleccionar asientos A1 y A2 sin estar logueado -> redirige a pedir correo (/compra/correo/)
        res_reserva = self.client.post(reverse("confiteria"), {
            "funcion_id": self.funcion.id,
            "asientos": ["A1", "A2"],
            "tipo_entrada": "general",
        })
        self.assertRedirects(res_reserva, reverse("compra_correo"))

        # Verificar que para otro cliente (otra sesión) A1 y A2 aparecen como "reservado" en la matriz
        otro_cliente = Client()
        res_otro = otro_cliente.get(reverse("asientos", args=[self.funcion.id]))
        mapa_otro = res_otro.context["mapa"]
        asientos_fila_a = {a["codigo"]: a["estado"] for a in mapa_otro[0]["asientos"]}
        self.assertEqual(asientos_fila_a["A1"], "reservado")
        self.assertEqual(asientos_fila_a["A2"], "reservado")

        # 3. Ingresar correo en la vista intermedia /compra/correo/
        res_correo = self.client.post(reverse("compra_correo"), {
            "correo": "comprador@correo.cl",
            "destino": "confiteria",
        })
        self.assertRedirects(res_correo, reverse("confiteria"))

        res_conf = self.client.get(reverse("confiteria"))
        self.assertContains(res_conf, "A1, A2")

        # 4. Agregar 1 producto de confitería -> ir a pago
        res_pago = self.client.post(reverse("pago"), {
            f"producto_{self.producto.id}": "1",
        })
        self.assertEqual(res_pago.status_code, 200)
        self.assertEqual(res_pago.context["resumen"]["total"], 20900)
        self.assertEqual(res_pago.context["correo_compra"], "comprador@correo.cl")

        # 5. Confirmar pago -> crea Compra, Entradas y DetalleConfiteria
        res_confirmar = self.client.post(reverse("pago"), {
            "confirmar_pago": "1",
            "medio": "debito",
        })
        compra = Compra.objects.get()
        self.assertRedirects(res_confirmar, reverse("entrada", args=[compra.id]))
        self.assertEqual(compra.total, 2 * 5500 + 9900)
        self.assertEqual(compra.entradas.count(), 2)
        self.assertEqual(compra.detalles_confiteria.count(), 1)
        self.assertEqual(compra.usuario.email, "comprador@correo.cl")

        # 6. Validar entrada desde el panel
        res_val = self.client.post(reverse("panel_validar"), {
            "codigo": f"{compra.numero}-A1",
        })
        self.assertEqual(res_val.status_code, 200)
        self.assertContains(res_val, "Entrada válida")

    def test_flujo_compra_usuario_autenticado_usa_correo_automaticamente(self):
        usuario = get_user_model().objects.create_user(
            username="registrado@correo.cl",
            email="registrado@correo.cl",
            password="T7!rK9#vQ2mL",
        )
        self.client.force_login(usuario)

        # Seleccionar asiento B1 estando logueado -> NO redirige a compra_correo, muestra confitería directo
        res_conf = self.client.post(reverse("confiteria"), {
            "funcion_id": self.funcion.id,
            "asientos": ["B1"],
            "tipo_entrada": "general",
        })
        self.assertEqual(res_conf.status_code, 200)
        self.assertEqual(self.client.session["compra_en_curso"]["correo"], "registrado@correo.cl")

        # Confirmar pago sin enviar campo correo -> usa el de la cuenta automáticamente
        res_confirmar = self.client.post(reverse("pago"), {
            "confirmar_pago": "1",
            "medio": "credito",
        })
        compra = Compra.objects.get(usuario=usuario)
        self.assertRedirects(res_confirmar, reverse("entrada", args=[compra.id]))
        self.assertEqual(compra.total, 5500)

    def test_panel_crud_peliculas_y_anulacion_venta(self):
        res_crear = self.client.post(reverse("panel_nuevo", args=["peliculas"]), {
            "nombre": "Película Nueva",
            "director": "Director X",
            "sinopsis": "Sinopsis prueba",
            "duracion": "95",
            "clasificacion": "TE",
            "fecha_estreno": self.hoy.isoformat(),
            "estado": "en_cartelera",
        })
        self.assertRedirects(res_crear, reverse("panel_listado", args=["peliculas"]))
        nueva = Pelicula.objects.get(nombre="Película Nueva")
        self.assertTrue(nueva.activa)

        # Dar de baja
        res_baja = self.client.post(reverse("panel_editar", args=["peliculas", nueva.id]), {
            "accion": "baja",
        })
        self.assertRedirects(res_baja, reverse("panel_listado", args=["peliculas"]))
        nueva.refresh_from_db()
        self.assertFalse(nueva.activa)

    def test_poblar_bd_y_todas_las_secciones_del_panel(self):
        call_command("poblar_bd")
        self.assertGreaterEqual(Pelicula.objects.count(), 9)
        self.assertGreaterEqual(Sala.objects.count(), 2)
        self.assertGreaterEqual(ProductoConfiteria.objects.count(), 8)

        res_dash = self.client.get(reverse("panel_dashboard"))
        self.assertEqual(res_dash.status_code, 200)

        for seccion in ("peliculas", "funciones", "salas", "productos", "ventas", "usuarios", "caja", "reportes"):
            res = self.client.get(reverse("panel_listado", args=[seccion]))
            self.assertEqual(res.status_code, 200)


class ApiRestTests(TestCase):
    def setUp(self):
        self.hoy = timezone.localdate()
        self.sala = Sala.objects.create(nombre_sala="Sala API")
        for n in range(1, 5):
            Asiento.objects.create(sala=self.sala, fila="A", numero=n)

        self.pelicula = Pelicula.objects.create(
            nombre="Pelicula API",
            sinopsis="Test API",
            fecha_estreno=self.hoy,
            duracion=120,
            clasificacion="TE",
            director="Director API",
            activa=True,
        )
        self.funcion = Funcion.objects.create(
            sala=self.sala,
            pelicula=self.pelicula,
            fecha_hora=timezone.now() + timedelta(hours=5),
            precio=5000,
        )
        self.producto = ProductoConfiteria.objects.create(
            nombre="Cabritas API",
            precio_unitario=3500,
            disponible=True,
        )

    def test_api_peliculas_get_y_post(self):
        res = self.client.get(reverse("api_peliculas"))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data["results"]), 1)

        res_post = self.client.post(
            reverse("api_peliculas"),
            data=json.dumps({
                "nombre": "Estreno JSON",
                "director": "Dir JSON",
                "fecha_estreno": self.hoy.isoformat(),
                "duracion": 110,
                "clasificacion": "+14",
            }),
            content_type="application/json",
        )
        self.assertEqual(res_post.status_code, 201)
        self.assertEqual(Pelicula.objects.count(), 2)

    def test_api_funcion_asientos_y_compra_atomica(self):
        # Consultar asientos disponibles
        res_asientos = self.client.get(reverse("api_funcion_asientos", args=[self.funcion.id]))
        self.assertEqual(res_asientos.status_code, 200)
        self.assertEqual(res_asientos.json()["disponibles"], 4)

        # Crear compra por API
        res_compra = self.client.post(
            reverse("api_compras"),
            data=json.dumps({
                "correo": "api@cliente.cl",
                "funcion_id": self.funcion.id,
                "asientos": ["A1", "A2"],
                "confiteria": [{"producto_id": self.producto.id, "cantidad": 2}],
            }),
            content_type="application/json",
        )
        self.assertEqual(res_compra.status_code, 201)
        compra_json = res_compra.json()
        self.assertEqual(compra_json["total"], 2 * 5000 + 2 * 3500)
        self.assertEqual(len(compra_json["entradas"]), 2)

        # Intentar comprar un asiento ya ocupado debe fallar con 400
        res_duplicada = self.client.post(
            reverse("api_compras"),
            data=json.dumps({
                "correo": "otro@cliente.cl",
                "funcion_id": self.funcion.id,
                "asientos": ["A1"],
            }),
            content_type="application/json",
        )
        self.assertEqual(res_duplicada.status_code, 400)

        # Verificar que quedan 2 asientos disponibles
        res_asientos_2 = self.client.get(reverse("api_funcion_asientos", args=[self.funcion.id]))
        self.assertEqual(res_asientos_2.json()["disponibles"], 2)

        # Validar entrada por API
        res_val = self.client.post(
            reverse("api_validar_entrada"),
            data=json.dumps({"codigo": f"{compra_json['numero']}-A1"}),
            content_type="application/json",
        )
        self.assertEqual(res_val.status_code, 200)
        self.assertTrue(res_val.json()["valido"])
