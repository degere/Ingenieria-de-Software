import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Usuario


User = get_user_model()


class UserApiTests(TestCase):
    password = "F9x!mV2qP8zL"

    def post_json(self, path, payload):
        return self.client.post(
            path,
            data=json.dumps(payload),
            content_type="application/json",
        )

    def register(self, email="cine@example.com", name="Vicente Vega"):
        return self.post_json(
            "/api/auth/register/",
            {
                "email": email,
                "password": self.password,
                "password_confirmation": self.password,
                "nombre_completo": name,
            },
        )

    def test_root_returns_api_status_and_endpoints(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertIn("/api/auth/register/", response.json()["endpoints"].values())

    def test_register_creates_auth_user_and_linked_profile(self):
        response = self.register()

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email="cine@example.com")
        profile = Usuario.objects.get(user=user)
        self.assertTrue(user.check_password(self.password))
        self.assertNotEqual(user.password, self.password)
        self.assertEqual(profile.nombre_completo, "Vicente Vega")
        self.assertEqual(profile.email, user.email)

    def test_register_rejects_duplicate_email_without_case_sensitivity(self):
        self.assertEqual(self.register().status_code, 201)

        response = self.register(email="CINE@example.com")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Usuario.objects.count(), 1)

    def test_login_profile_update_and_password_change(self):
        self.assertEqual(self.register().status_code, 201)

        login_response = self.post_json(
            "/api/auth/login/",
            {"email": "CINE@example.com", "password": self.password},
        )
        self.assertEqual(login_response.status_code, 200)

        profile_response = self.post_json("/api/users/me/", {})
        self.assertEqual(profile_response.status_code, 405)

        profile_response = self.client.patch(
            "/api/users/me/",
            data=json.dumps(
                {"email": "vicente@example.com", "nombre_completo": "Vicente Vega"}
            ),
            content_type="application/json",
        )
        self.assertEqual(profile_response.status_code, 200)
        user = User.objects.get(email="vicente@example.com")
        profile = Usuario.objects.get(user=user)
        self.assertEqual(profile.email, "vicente@example.com")
        self.assertEqual(profile.nombre_completo, "Vicente Vega")

        new_password = "K7r!qN4xB2mV"
        change_response = self.post_json(
            "/api/users/me/password/",
            {
                "current_password": self.password,
                "new_password": new_password,
                "password_confirmation": new_password,
            },
        )
        self.assertEqual(change_response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.check_password(new_password))
