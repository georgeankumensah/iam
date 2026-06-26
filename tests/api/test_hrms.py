import pytest

from lifecycle.models import HrmsEvent

pytestmark = pytest.mark.django_db


def test_hrms_events_list(admin_client):
    HrmsEvent.objects.create(event_type="hrms.joiner", target_email="a@b.com", payload={})
    HrmsEvent.objects.create(event_type="hrms.leaver", target_email="b@b.com", payload={})
    resp = admin_client.get("/v1/admin/hrms-events")
    assert resp.status_code == 200
    assert resp.data["success"] is True
    assert len(resp.data["data"]) == 2


def test_hrms_events_filter_by_status(admin_client):
    HrmsEvent.objects.create(event_type="hrms.joiner", target_email="a@b.com", status="failed")
    HrmsEvent.objects.create(event_type="hrms.joiner", target_email="b@b.com", status="processed")
    resp = admin_client.get("/v1/admin/hrms-events?status=failed")
    assert resp.status_code == 200
    assert len(resp.data["data"]) == 1


def test_hrms_events_filter_by_event_type(admin_client):
    HrmsEvent.objects.create(event_type="hrms.joiner", target_email="a@b.com", payload={})
    HrmsEvent.objects.create(event_type="hrms.leaver", target_email="b@b.com", payload={})
    resp = admin_client.get("/v1/admin/hrms-events?event_type=hrms.leaver")
    assert resp.status_code == 200
    assert len(resp.data["data"]) == 1
    assert resp.data["data"][0]["event_type"] == "hrms.leaver"


def test_hrms_events_search_by_email(admin_client):
    HrmsEvent.objects.create(event_type="hrms.joiner", target_email="alice@clet.gov.gh", payload={})
    HrmsEvent.objects.create(event_type="hrms.joiner", target_email="bob@clet.gov.gh", payload={})
    resp = admin_client.get("/v1/admin/hrms-events?email=alice")
    assert resp.status_code == 200
    assert len(resp.data["data"]) == 1


def test_hrms_event_replay(admin_client):
    event = HrmsEvent.objects.create(event_type="hrms.joiner", target_email="a@b.com")
    resp = admin_client.post(f"/v1/admin/hrms-events/{event.id}/replay")
    assert resp.status_code == 200
    assert resp.data["success"] is True
    event.refresh_from_db()
    assert event.replay_count == 1


def test_hrms_event_replay_not_found(admin_client):
    resp = admin_client.post("/v1/admin/hrms-events/00000000-0000-0000-0000-000000000000/replay")
    assert resp.status_code == 404


def test_hrms_move_conflicts(admin_client):
    HrmsEvent.objects.create(event_type="hrms.mover", target_email="a@b.com", status="conflict")
    HrmsEvent.objects.create(event_type="hrms.mover", target_email="b@b.com", status="processed")
    resp = admin_client.get("/v1/admin/hrms-events/move-conflicts")
    assert resp.status_code == 200
    assert len(resp.data["data"]) == 1


def test_hrms_move_conflict_resolve(admin_client):
    from accounts.models import User
    admin_user = User.objects.get(email="admin@clet.gov.gh")
    event = HrmsEvent.objects.create(
        event_type="hrms.mover", target_email="a@b.com", status="conflict", payload={}
    )
    resp = admin_client.post(
        f"/v1/admin/hrms-events/{event.id}/resolve",
        {"action": "dismiss", "note": "resolved manually"},
        format="json",
    )
    assert resp.status_code == 200
    event.refresh_from_db()
    assert event.status == "resolved"
    assert event.resolved_by == admin_user
    assert event.resolution_note == "resolved manually"


def test_hrms_move_conflict_resolve_replay(admin_client):
    event = HrmsEvent.objects.create(
        event_type="hrms.mover", target_email="a@b.com", status="conflict", payload={}
    )
    resp = admin_client.post(
        f"/v1/admin/hrms-events/{event.id}/resolve",
        {"action": "replay", "note": "retry"},
        format="json",
    )
    assert resp.status_code == 200
    event.refresh_from_db()
    assert event.status == "resolved"


def test_hrms_move_conflict_resolve_not_conflict(admin_client):
    event = HrmsEvent.objects.create(event_type="hrms.mover", target_email="a@b.com", status="processed")
    resp = admin_client.post(
        f"/v1/admin/hrms-events/{event.id}/resolve",
        {"action": "dismiss"},
        format="json",
    )
    assert resp.status_code == 409


def test_unauthorized_access(api_client):
    resp = api_client.get("/v1/admin/hrms-events")
    assert resp.status_code == 401
