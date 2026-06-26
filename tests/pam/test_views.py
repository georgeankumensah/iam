
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from pam.models import PamSession

User = get_user_model()


class PAMViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="pamuser@clet.gov.gh", user_type="staff", status="active")
        self.client.force_authenticate(user=self.user)
        PamSession.objects.create(
            user=self.user,
            target_id="db-prod-01",
            started_at=timezone.now(),
        )

    def test_list_sessions(self):
        resp = self.client.get("/pam/sessions")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["data"]), 1)

    @override_settings(
        PAM_VAULT_ADDR="",
    )
    def test_start_session(self):
        resp = self.client.post("/pam/sessions", {"target_id": "db-prod-02", "target_host": "db2.example.com"})
        self.assertEqual(resp.status_code, 201)
        data = resp.data
        self.assertEqual(data["status"], "active")
        self.assertIn("id", data)

    def test_start_session_missing_target_id(self):
        resp = self.client.post("/pam/sessions", {})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("target_id", resp.data["error"])

    def test_end_session(self):
        session = PamSession.objects.first()
        resp = self.client.post(
            f"/pam/sessions/{session.id}/end",
            {"recording_uri": "http://rec.example.com/rec-1", "recording_sha256": "hash123"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["status"], "ended")
        session.refresh_from_db()
        self.assertEqual(session.status, PamSession.SessionStatus.ENDED)
        self.assertEqual(session.recording_sha256, "hash123")

    def test_end_session_not_found(self):
        resp = self.client.post("/pam/sessions/00000000-0000-0000-0000-000000000000/end", {})
        self.assertEqual(resp.status_code, 404)

    def test_end_session_wrong_user(self):
        other = User.objects.create_user(email="other@clet.gov.gh", user_type="staff", status="active")
        session = PamSession.objects.create(user=other, target_id="other-host", started_at=timezone.now())
        resp = self.client.post(f"/pam/sessions/{session.id}/end", {})
        self.assertEqual(resp.status_code, 404)


class PAMRevokeViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="admin-pam@clet.gov.gh", user_type="staff", status="active")
        self.client.force_authenticate(user=self.user)
        self.session = PamSession.objects.create(
            user=self.user,
            target_id="db-prod-01",
            started_at=timezone.now(),
        )

    def test_revoke_requires_step_up_mfa(self):
        resp = self.client.post(f"/pam/sessions/{self.session.id}/revoke", {"reason": "test"})
        self.assertEqual(resp.status_code, 401)
        self.assertIn("STEP_UP_REQUIRED", resp.data["errors"]["code"])

    def test_revoke_not_found(self):
        resp = self.client.post("/pam/sessions/00000000-0000-0000-0000-000000000000/revoke", {})
        self.assertEqual(resp.status_code, 401)

    def test_revoke_with_step_up(self):
        mock_auth = type("Auth", (), {"mfa_verified": True})()
        self.client.force_authenticate(user=self.user, token=mock_auth)
        resp = self.client.post(f"/pam/sessions/{self.session.id}/revoke", {"reason": "test"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["status"], "revoked")
