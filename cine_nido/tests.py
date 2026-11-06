from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


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
