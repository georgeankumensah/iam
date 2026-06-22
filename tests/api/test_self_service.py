from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


class SelfServiceEndpointTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_me_requires_auth(self) -> None:
        resp = self.client.get("/v1/me")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_authenticated(self) -> None:
        user = User.objects.create_user(email="staff@test.gov", user_type="staff", status="active")
        self.client.force_authenticate(user=user)
        resp = self.client.get("/v1/me")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["data"]["email"], "staff@test.gov")
