from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from rbac.models import Role

User = get_user_model()


class AdminRolesEndpointTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin@test.gov",
            user_type="staff",
            status="active",
            is_staff=True,
            is_superuser=True,
        )
        self.role = Role.objects.create(
            system_code="IAM",
            role_id="iam-admin",
            name="IAM Administrator",
            permission_strings=["iam.*"],
        )

    def test_list_roles(self) -> None:
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get("/v1/admin/roles")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.json()["success"])

    def test_create_role(self) -> None:
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post("/v1/admin/roles", {
            "system_code": "PORTAL",
            "role_id": "portal-user",
            "name": "Portal User",
            "permission_strings": ["portal.read"],
        }, content_type="application/json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_bind_role(self) -> None:
        self.client.force_authenticate(user=self.admin)
        user = User.objects.create_user(email="target@test.gov", user_type="staff", status="active")
        resp = self.client.post(f"/v1/admin/roles/{self.role.id}/bind", {
            "user_id": str(user.id),
            "justification": "Test binding",
        }, content_type="application/json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
