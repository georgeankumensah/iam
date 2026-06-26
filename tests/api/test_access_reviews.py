import pytest

from accounts.models import User
from clients.models import OIDCClient
from rbac.models import AccessReviewCampaign, Role, RoleBinding

pytestmark = pytest.mark.django_db


@pytest.fixture
def gov_grant():
    OIDCClient.objects.create(client_id="c-gov", system_code="gov", name="GOV",
                              zitadel_project_id="proj-gov", zitadel_app_id="app-gov")
    registrar = Role.objects.create(system_code="gov", role_id="registrar", name="Registrar")
    member = User.objects.create(email="g@clet.gov.gh", status="active",
                                 zitadel_user_id="100000000000000011")
    RoleBinding.objects.create(role=registrar, user=member, state="approved")
    return member, registrar


def test_campaign_create_generates_items(admin_client, gov_grant):
    resp = admin_client.post(
        "/v1/admin/access-reviews",
        {"name": "Gov Q2", "period": "2026-Q2", "scope": {"system_code": "gov"}},
        format="json",
    )
    assert resp.status_code == 201, resp.content
    cid = resp.json()["data"]["id"]
    assert resp.json()["data"]["items_generated"] == 1
    items = admin_client.get(f"/v1/admin/access-reviews/{cid}/items").json()["data"]
    assert len(items) == 1


def test_revoke_decision_revokes_binding(admin_client, gov_grant, mock_zitadel):
    member, registrar = gov_grant
    c = AccessReviewCampaign.objects.create(name="r", period="2026-Q2", scope={"system_code": "gov"})
    from rbac.review_services import generate_items
    generate_items(c)
    item = c.items.first()
    resp = admin_client.post(f"/v1/admin/access-review-items/{item.id}/decide",
                             {"decision": "revoke"}, format="json")
    assert resp.status_code == 200
    assert RoleBinding.objects.get(role=registrar, user=member).state == "revoked"
    mock_zitadel.find_user_grant.assert_called()


def test_complete_requires_all_decided_then_signs(admin_client, gov_grant):
    c = AccessReviewCampaign.objects.create(name="r", period="2026-Q2", scope={"system_code": "gov"})
    from rbac.review_services import generate_items
    generate_items(c)
    # Not decided yet -> conflict
    r1 = admin_client.post(f"/v1/admin/access-reviews/{c.id}/complete", {}, format="json")
    assert r1.status_code == 409
    # Decide all, then complete
    for item in c.items.all():
        admin_client.post(f"/v1/admin/access-review-items/{item.id}/decide",
                          {"decision": "keep"}, format="json")
    r2 = admin_client.post(f"/v1/admin/access-reviews/{c.id}/complete", {}, format="json")
    assert r2.status_code == 200
    digest = r2.json()["data"]["digest"]
    assert len(digest) == 64
    export = admin_client.get(f"/v1/admin/access-reviews/{c.id}/export").json()["data"]
    assert export["digest"] == digest
