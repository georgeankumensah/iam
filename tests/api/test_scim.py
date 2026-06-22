from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


class ScimEndpointTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.auth_header = f"Bearer {settings.SCIM_BEARER_TOKEN}"

    def test_create_user_unauthorized(self) -> None:
        resp = self.client.post("/scim/v2/Users", {"userName": "test@example.com"}, content_type="application/json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_user_detail_not_found(self) -> None:
        resp = self.client.get(
            "/scim/v2/Users/00000000-0000-0000-0000-000000000000",
            HTTP_AUTHORIZATION=self.auth_header,
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_user_detail_with_invalid_token(self) -> None:
        resp = self.client.get(
            "/scim/v2/Users/00000000-0000-0000-0000-000000000000",
            HTTP_AUTHORIZATION="Bearer wrong-token",
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
