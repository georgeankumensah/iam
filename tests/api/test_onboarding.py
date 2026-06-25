import pytest

from accounts.models import Invitation, User
from clients.models import OIDCClient
from rbac.models import Role, RoleBinding

pytestmark = pytest.mark.django_db


@pytest.fixture
def ams_system():
    client = OIDCClient.objects.create(
        client_id="client-ams", system_code="ams", name="AMS",
        zitadel_project_id="proj-ams", zitadel_app_id="app-ams",
        redirect_uris=["http://localhost:5173/login/callback"],
    )
    user_role = Role.objects.create(system_code="ams", role_id="user", name="AMS User", is_admin=False)
    admin_role = Role.objects.create(system_code="ams", role_id="admin", name="AMS Admin", is_admin=True)
    return client, user_role, admin_role


def test_invite_requires_email_and_system(admin_client):
    resp = admin_client.post("/v1/invitations", {"email": ""}, format="json")
    assert resp.status_code == 400
    assert resp.json()["success"] is False


def test_invite_creates_user_grant_and_invitation(admin_client, ams_system, mock_zitadel):
    _, user_role, _ = ams_system
    resp = admin_client.post(
        "/v1/invitations",
        {"email": "invitee@clet.gov.gh", "system_code": "ams",
         "role_ids": [str(user_role.id)], "return_code": True},
        format="json",
    )
    assert resp.status_code == 201, resp.content
    data = resp.json()["data"]
    assert data["email"] == "invitee@clet.gov.gh"
    assert data["invite_code"] == "RESETCODE"
    # User mirrored + pending invitation + approved binding + grant pushed
    user = User.objects.get(email="invitee@clet.gov.gh")
    assert user.zitadel_user_id == "100000000000000001"
    assert Invitation.objects.filter(email="invitee@clet.gov.gh", status="pending").exists()
    assert RoleBinding.objects.filter(user=user, role=user_role, state="approved").exists()
    mock_zitadel.upsert_user_grant.assert_called()


def test_invite_requires_role(admin_client, ams_system):
    resp = admin_client.post(
        "/v1/invitations",
        {"email": "x@clet.gov.gh", "system_code": "ams", "role_ids": []},
        format="json",
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "role_required"


def test_invite_unknown_system(admin_client):
    resp = admin_client.post(
        "/v1/invitations",
        {"email": "x@clet.gov.gh", "system_code": "nope", "role_ids": ["x"]},
        format="json",
    )
    assert resp.status_code in (400, 403)


def test_non_admin_cannot_invite(auth_client, ams_system):
    _, user_role, _ = ams_system
    resp = auth_client.post(
        "/v1/invitations",
        {"email": "x@clet.gov.gh", "system_code": "ams", "role_ids": [str(user_role.id)]},
        format="json",
    )
    assert resp.status_code == 403


def test_my_admin_systems_lists_for_superadmin(admin_client, ams_system):
    resp = admin_client.get("/v1/me/admin-systems")
    assert resp.status_code == 200
    codes = [s["system_code"] for s in resp.json()["data"]]
    assert "ams" in codes


def test_accept_invitation_activates_user(admin_client, ams_system, mock_zitadel, settings):
    user = User.objects.create(email="acc@clet.gov.gh", status="pre_active",
                               zitadel_user_id="100000000000000009")
    Invitation.objects.create(email="acc@clet.gov.gh", system_code="ams", user=user,
                              zitadel_user_id="100000000000000009", status="pending")
    from rest_framework.test import APIClient
    client = APIClient()
    resp = client.post(
        "/v1/onboarding/accept",
        {"zitadel_user_id": "100000000000000009", "code": "RESETCODE", "password": "Test1234!"},
        format="json",
        HTTP_X_INTERNAL_SECRET=settings.ONBOARDING_INTERNAL_SECRET,
    )
    assert resp.status_code == 200, resp.content
    user.refresh_from_db()
    assert user.status == "active"
    mock_zitadel.set_password_with_code.assert_called_once()


def test_accept_rejects_bad_secret(settings):
    from rest_framework.test import APIClient
    client = APIClient()
    resp = client.post(
        "/v1/onboarding/accept",
        {"zitadel_user_id": "1", "code": "x", "password": "y"},
        format="json",
        HTTP_X_INTERNAL_SECRET="wrong",
    )
    assert resp.status_code == 403
