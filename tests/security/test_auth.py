from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


class SecurityTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_admin_endpoints_require_auth(self) -> None:
        endpoints = [
            "/v1/admin/users",
            "/v1/admin/roles",
            "/v1/admin/clients",
            "/v1/admin/audit",
        ]
        for endpoint in endpoints:
            resp = self.client.get(endpoint)
            self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED, f"{endpoint} should require auth")

    def test_disabled_user_is_not_active(self) -> None:
        user = User.objects.create_user(email="disabled@test.gov", user_type="staff", status="disabled")
        self.assertFalse(user.is_active)

    def test_active_user_is_active(self) -> None:
        user = User.objects.create_user(email="active@test.gov", user_type="staff", status="active")
        self.assertTrue(user.is_active)

    def test_security_headers(self) -> None:
        resp = self.client.get("/health/live")
        self.assertEqual(resp["X-Content-Type-Options"], "nosniff")
        self.assertEqual(resp["X-Frame-Options"], "DENY")

    def test_unauthenticated_get_on_me_returns_401(self) -> None:
        resp = self.client.get("/v1/me")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
