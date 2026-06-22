from django.test import TestCase
from rest_framework.test import APIClient


class HealthEndpointTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_liveness(self) -> None:
        resp = self.client.get("/health/live")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "alive")

    def test_readiness(self) -> None:
        resp = self.client.get("/health/ready")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "ready")
