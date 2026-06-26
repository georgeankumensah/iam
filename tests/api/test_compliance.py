import pytest

from compliance.models import DPIA, DataResidency

pytestmark = pytest.mark.django_db


class TestDataResidency:
    def test_list_residency_empty(self, admin_client):
        resp = admin_client.get("/v1/admin/residency/")
        assert resp.status_code == 200
        assert resp.data["data"] == []

    def test_create_residency_record(self, admin_client):
        resp = admin_client.post(
            "/v1/admin/residency/",
            {"service_name": "PostgreSQL", "region": "ghana",
             "data_classification": "confidential"},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["data"][0]["service_name"] == "PostgreSQL"

    def test_create_residency_duplicate_updates(self, admin_client):
        DataResidency.objects.create(service_name="Redis", region="eu-west-2")
        resp = admin_client.post(
            "/v1/admin/residency/",
            {"service_name": "Redis", "region": "ghana"},
            format="json",
        )
        assert resp.status_code == 200
        assert DataResidency.objects.count() == 1
        assert DataResidency.objects.get(service_name="Redis").region == "ghana"

    def test_residency_review(self, admin_client):
        from accounts.models import User
        r = DataResidency.objects.create(service_name="Zitadel DB", region="eu-west-2")
        resp = admin_client.post(f"/v1/admin/residency/{r.id}/review", {}, format="json")
        assert resp.status_code == 200
        r.refresh_from_db()
        assert r.last_reviewed_at is not None
        assert r.reviewed_by == User.objects.get(email="admin@clet.gov.gh")

    def test_residency_review_not_found(self, admin_client):
        resp = admin_client.post(
            "/v1/admin/residency/00000000-0000-0000-0000-000000000000/review",
            {}, format="json",
        )
        assert resp.status_code == 404

    def test_list_residency_shows_records(self, admin_client):
        DataResidency.objects.create(service_name="Redis", region="us-east-1")
        DataResidency.objects.create(service_name="PostgreSQL", region="ghana")
        resp = admin_client.get("/v1/admin/residency/")
        assert resp.status_code == 200
        assert len(resp.data["data"]) == 2


class TestDPIA:
    def test_list_dpia_empty(self, admin_client):
        resp = admin_client.get("/v1/admin/residency/dpia")
        assert resp.status_code == 200
        assert resp.data["data"] == []

    def test_create_dpia_draft(self, admin_client):
        resp = admin_client.post(
            "/v1/admin/residency/dpia",
            {"title": "IAM Platform DPIA", "document_ref": "DPIA-2026-001"},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["data"][0]["status"] == "draft"

    def test_create_dpia_signed(self, admin_client):
        resp = admin_client.post(
            "/v1/admin/residency/dpia",
            {
                "title": "IAM Platform DPIA",
                "document_ref": "DPIA-2026-001",
                "sign": True,
                "review_date": "2027-06-26T00:00:00Z",
            },
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["data"][0]["status"] == "signed"

    def test_list_dpia_shows_records(self, admin_client):
        DPIA.objects.create(title="DPIA 1", status="draft")
        DPIA.objects.create(title="DPIA 2", status="signed")
        resp = admin_client.get("/v1/admin/residency/dpia")
        assert resp.status_code == 200
        assert len(resp.data["data"]) == 2

    def test_unauthorized_access(self, api_client):
        resp = api_client.get("/v1/admin/residency/")
        assert resp.status_code == 401
