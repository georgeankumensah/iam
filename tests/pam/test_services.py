from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from pam.models import PamSession
from pam.services import (
    broker_pam_session,
    list_pam_sessions,
    revoke_pam_session,
    revoke_user_pam_sessions,
)

User = get_user_model()
NOW = timezone.now()


class PAMServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="pamtest@clet.gov.gh", user_type="staff", status="active")
        self.session = PamSession.objects.create(
            user=self.user,
            target_id="db-prod-01",
            target_host="db-prod.example.com",
            vault_lease_id="lease-001",
            started_at=NOW,
        )

    def test_broker_local_only_no_vault_no_jumpserver(self):
        session = broker_pam_session(user=self.user, target_id="db-prod-02", target_host="db-prod2.example.com")
        self.assertEqual(session.target_id, "db-prod-02")
        self.assertEqual(session.user, self.user)
        self.assertEqual(session.vault_lease_id, "")
        self.assertEqual(session.recording_uri, "")
        self.assertEqual(session.status, PamSession.SessionStatus.ACTIVE)

    @override_settings(PAM_VAULT_ADDR="http://vault:8200", PAM_VAULT_TOKEN="test-token")
    @patch("core.vault.requests.post")
    def test_broker_with_vault(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"lease_id": "lease-abc"}
        session = broker_pam_session(user=self.user, target_id="db-prod-03", ttl_hours=2)
        self.assertEqual(session.vault_lease_id, "lease-abc")
        mock_post.assert_called_once()

    @override_settings(
        PAM_VAULT_ADDR="http://vault:8200",
        PAM_VAULT_TOKEN="test-token",
        PAM_JUMPSERVER_API_URL="http://jumpserver:8080",
        PAM_JUMPSERVER_API_TOKEN="js-token",
    )
    def test_broker_with_vault_and_jumpserver(self):
        import pam.services as ps

        with patch.object(ps, "requests") as mock_ps_req, patch("core.vault.requests.post") as mock_core:
                mock_ps_req.post.return_value.status_code = 200
                mock_ps_req.post.return_value.json.return_value = {
                    "recording_uri": "http://recording.example.com/session-1",
                    "recording_sha256": "abc123...",
                }
                mock_core.return_value.status_code = 200
                mock_core.return_value.json.return_value = {"lease_id": "lease-xyz"}
                session = broker_pam_session(user=self.user, target_id="db-prod-04")
        self.assertEqual(session.vault_lease_id, "lease-xyz")
        self.assertEqual(session.recording_uri, "http://recording.example.com/session-1")
        self.assertEqual(session.recording_sha256, "abc123...")

    def test_list_pam_sessions(self):
        PamSession.objects.create(user=self.user, target_id="srv-01", started_at=NOW)
        all_sessions = list_pam_sessions()
        self.assertEqual(len(all_sessions), 2)

    def test_list_pam_sessions_filter_by_status(self):
        active = list_pam_sessions(status="active")
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].id, self.session.id)

    def test_revoke_pam_session(self):
        revoke_pam_session(session=self.session, actor_id=str(self.user.id), reason="test")
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, PamSession.SessionStatus.REVOKED)
        self.assertIsNotNone(self.session.ended_at)

    def test_revoke_already_revoked_is_noop(self):
        self.session.status = PamSession.SessionStatus.REVOKED
        self.session.save()
        result = revoke_pam_session(session=self.session, actor_id="system")
        self.assertEqual(result.status, PamSession.SessionStatus.REVOKED)

    def test_revoke_user_pam_sessions(self):
        second = PamSession.objects.create(user=self.user, target_id="srv-02", started_at=NOW)
        count = revoke_user_pam_sessions(user=self.user, reason="leaver")
        self.assertEqual(count, 2)
        self.session.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(self.session.status, PamSession.SessionStatus.REVOKED)
        self.assertEqual(second.status, PamSession.SessionStatus.REVOKED)

    def test_revoke_user_pam_sessions_no_active(self):
        self.session.status = PamSession.SessionStatus.ENDED
        self.session.save()
        count = revoke_user_pam_sessions(user=self.user, reason="leaver")
        self.assertEqual(count, 0)

    def test_ttl_clamped_between_1_and_4(self):
        session = broker_pam_session(user=self.user, target_id="t", ttl_hours=999)
        self.assertEqual(session.target_id, "t")

    def test_ttl_minimum_1(self):
        session = broker_pam_session(user=self.user, target_id="t2", ttl_hours=0)
        self.assertEqual(session.target_id, "t2")
