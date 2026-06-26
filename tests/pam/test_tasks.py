from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from pam.models import PamSession

User = get_user_model()


class PAMTaskTests(TestCase):
    def test_cleanup_stale_pam_sessions(self):
        from pam.tasks import cleanup_stale_pam_sessions

        user = User.objects.create_user(email="stale@clet.gov.gh", user_type="staff", status="active")
        PamSession.objects.create(
            user=user,
            target_id="stale-host",
            started_at=timezone.now() - timedelta(hours=48),
        )
        result = cleanup_stale_pam_sessions()
        self.assertEqual(result["stale_sessions_ended"], 1)

    def test_cleanup_only_stale(self):
        from pam.tasks import cleanup_stale_pam_sessions

        user = User.objects.create_user(email="fresh@clet.gov.gh", user_type="staff", status="active")
        PamSession.objects.create(
            user=user,
            target_id="fresh-host",
            started_at=timezone.now() - timedelta(hours=1),
        )
        result = cleanup_stale_pam_sessions()
        self.assertEqual(result["stale_sessions_ended"], 0)

    def test_anchor_recording_hashes_daily_no_recordings(self):
        from pam.tasks import anchor_recording_hashes_daily

        result = anchor_recording_hashes_daily()
        self.assertEqual(result["anchored_count"], 0)

    def test_anchor_recording_hashes_daily(self):
        from pam.tasks import anchor_recording_hashes_daily

        user = User.objects.create_user(email="rec@clet.gov.gh", user_type="staff", status="active")
        PamSession.objects.create(
            user=user,
            target_id="rec-host",
            status=PamSession.SessionStatus.ENDED,
            recording_sha256="abc123def456",
            started_at=timezone.now() - timedelta(hours=2),
            ended_at=timezone.now(),
        )
        result = anchor_recording_hashes_daily()
        self.assertEqual(result["anchored_count"], 1)
        self.assertIn("root_hash", result)

    def test_anchor_skips_active_sessions(self):
        from pam.tasks import anchor_recording_hashes_daily

        user = User.objects.create_user(email="active-rec@clet.gov.gh", user_type="staff", status="active")
        PamSession.objects.create(
            user=user,
            target_id="active-host",
            status=PamSession.SessionStatus.ACTIVE,
            recording_sha256="should-skip",
            started_at=timezone.now(),
        )
        result = anchor_recording_hashes_daily()
        self.assertEqual(result["anchored_count"], 0)
