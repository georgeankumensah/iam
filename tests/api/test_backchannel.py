import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from audit.models import ActiveSession

User = get_user_model()
pytestmark = pytest.mark.django_db

NOW = timezone.now()


def test_backchannel_logout_missing_token():
    c = Client()
    resp = c.post("/backchannel-logout", {})
    assert resp.status_code == 400
    assert resp.json()["error"] == "missing_token"


def test_backchannel_logout_invalid_token():
    c = Client()
    resp = c.post("/backchannel-logout", {"logout_token": "garbage"})
    assert resp.status_code == 500


def _make_backchannel_payload(**overrides):
    return {
        "sub": "00000000-0000-0000-0000-000000000001",
        "sid": "session-1",
        "events": {"http://schemas.openid.net/event/backchannel-logout": {}},
        **overrides,
    }


def test_backchannel_logout_unknown_user():
    from unittest.mock import patch
    c = Client()
    with patch("oidc_rp.backchannel.verify_jwt_token", return_value=_make_backchannel_payload()):
        resp = c.post("/backchannel-logout", {"logout_token": "fake"})
    assert resp.status_code == 200


def test_backchannel_logout_revokes_sessions():
    from unittest.mock import patch
    user = User.objects.create_user(email="test@clet.gov.gh", user_type="staff", status="active")
    ActiveSession.objects.create(user=user, jti="session-1", issued_at=NOW)
    c = Client()
    with patch("oidc_rp.backchannel.verify_jwt_token",
               return_value=_make_backchannel_payload(sub=user.zitadel_user_id or str(user.id))):
        resp = c.post("/backchannel-logout", {"logout_token": "fake"})
    assert resp.status_code == 200
    assert ActiveSession.objects.filter(revoked=True).count() == 1


def test_backchannel_logout_failure_metric():
    from core.metrics import backchannel_logout_failures_total
    before = backchannel_logout_failures_total._value.get()
    c = Client()
    c.post("/backchannel-logout", {"logout_token": "garbage"})
    after = backchannel_logout_failures_total._value.get()
    assert after > before
