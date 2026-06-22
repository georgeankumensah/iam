from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


class AdminUsersEndpointTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin@test.gov",
            user_type="staff",
            status="active",
            is_staff=True,
            is_superuser=True,
        )

    def test_list_users_requires_auth(self) -> None:
        resp = self.client.get("/v1/admin/users")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_users_authenticated(self) -> None:
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get("/v1/admin/users")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.json()["success"])

    def test_filter_by_user_type(self) -> None:
        User.objects.create_user(email="student@test.edu", user_type="student", status="active")
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get("/v1/admin/users?user_type=student")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_search_by_email(self) -> None:
        User.objects.create_user(email="findme@test.gov", user_type="staff", status="active")
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get("/v1/admin/users?search=findme")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
