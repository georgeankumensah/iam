import hashlib

import pytest
from django.utils import timezone

from accounts.models import Invitation, User
from clients.models import OIDCClient
from rbac.models import Role, RoleBinding

pytestmark = pytest.mark.django_db

_TEST_LOOKUP_TOKEN = "test-lookup-token-test"
_TEST_LOOKUP_HASH = hashlib.sha256(_TEST_LOOKUP_TOKEN.encode()).hexdigest()


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
         "role_id": str(user_role.id), "return_code": True,
         "first_name": "Jane", "last_name": "Doe"},
        format="json",
    )
    assert resp.status_code == 201, resp.content
    assert resp.json()["message"] == "Invite sent."
    data = resp.json()["data"]
    assert data["email"] == "invitee@clet.gov.gh"
    assert data["role_id"] == str(user_role.id)
    assert data["system_code"] == "ams"
    assert data["assignment_id"] is not None
    # User mirrored + pending invitation + approved binding + grant pushed
    user = User.objects.get(email="invitee@clet.gov.gh")
    assert user.zitadel_user_id == "100000000000000001"
    assert Invitation.objects.filter(email="invitee@clet.gov.gh", status="pending").exists()
    assert RoleBinding.objects.filter(user=user, role=user_role, state="approved").exists()
    mock_zitadel.upsert_user_grant.assert_called()


def test_invite_requires_role(admin_client, ams_system):
    _ = ams_system
    resp = admin_client.post(
        "/v1/invitations",
        {"email": "x@clet.gov.gh", "system_code": "ams"},
        format="json",
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "email, system_code and role_id are required"


def test_invite_unknown_system(admin_client):
    resp = admin_client.post(
        "/v1/invitations",
        {"email": "x@clet.gov.gh", "system_code": "nope",
         "role_id": "00000000-0000-0000-0000-000000000000"},
        format="json",
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "unknown_system"


def test_non_admin_cannot_invite(auth_client, ams_system):
    _, user_role, _ = ams_system
    resp = auth_client.post(
        "/v1/invitations",
        {"email": "x@clet.gov.gh", "system_code": "ams",
         "role_id": str(user_role.id)},
        format="json",
    )
    assert resp.status_code == 403


def test_my_admin_systems_lists_for_superadmin(admin_client, ams_system):
    _ = ams_system
    resp = admin_client.get("/v1/me/admin-systems")
    assert resp.status_code == 200
    codes = [s["system_code"] for s in resp.json()["data"]]
    assert "ams" in codes


def test_internal_admin_systems_uses_zitadel_actor(admin_user, ams_system, settings):
    _ = ams_system
    admin_user.zitadel_user_id = "admin-zid"
    admin_user.save(update_fields=["zitadel_user_id"])

    from rest_framework.test import APIClient

    client = APIClient()
    resp = client.get(
        "/v1/internal/admin-systems",
        {"actor_zitadel_user_id": "admin-zid"},
        HTTP_X_INTERNAL_SECRET=settings.ONBOARDING_INTERNAL_SECRET,
    )

    assert resp.status_code == 200
    assert "ams" in [s["system_code"] for s in resp.json()["data"]]


def test_internal_invitation_creates_dev_invite(admin_user, ams_system, mock_zitadel, settings):
    _, user_role, _ = ams_system
    admin_user.zitadel_user_id = "admin-zid"
    admin_user.save(update_fields=["zitadel_user_id"])

    from rest_framework.test import APIClient

    client = APIClient()
    resp = client.post(
        "/v1/internal/invitations",
        {
            "actor_zitadel_user_id": "admin-zid",
            "email": "new@clet.gov.gh",
            "system_code": "ams",
            "role_ids": [str(user_role.id)],
            "return_code": True,
        },
        format="json",
        HTTP_X_INTERNAL_SECRET=settings.ONBOARDING_INTERNAL_SECRET,
    )

    assert resp.status_code == 201, resp.content
    assert resp.json()["data"]["invite_code"] == "RESETCODE"
    mock_zitadel.upsert_user_grant.assert_called()


def test_internal_invitation_resend_reopens_invite(admin_user, ams_system, mock_zitadel, settings):
    _, user_role, _ = ams_system
    admin_user.zitadel_user_id = "admin-zid"
    admin_user.save(update_fields=["zitadel_user_id"])
    user = User.objects.create(
        email="stale@clet.gov.gh",
        status="pre_active",
        zitadel_user_id="100000000000000011",
    )
    invitation = Invitation.objects.create(
        email=user.email,
        system_code="ams",
        user=user,
        zitadel_user_id=user.zitadel_user_id,
        role_ids=[str(user_role.id)],
        status=Invitation.Status.ACCEPTED,
        accepted_at=timezone.now(),
        expires_at=timezone.now(),
    )

    from rest_framework.test import APIClient

    client = APIClient()
    resp = client.post(
        f"/v1/internal/invitations/{invitation.id}/resend",
        {"actor_zitadel_user_id": "admin-zid"},
        format="json",
        HTTP_X_INTERNAL_SECRET=settings.ONBOARDING_INTERNAL_SECRET,
    )

    assert resp.status_code == 200, resp.content
    data = resp.json()["data"]
    assert data["invite_code"] == "RESETCODE"
    assert data["status"] == Invitation.Status.PENDING
    invitation.refresh_from_db()
    assert invitation.status == Invitation.Status.PENDING
    assert invitation.accepted_at is None
    assert invitation.expires_at > timezone.now()
    mock_zitadel.request_password_set.assert_called_with(
        "100000000000000011",
        url_template=None,
        return_code=True,
    )


def test_accept_invitation_activates_user(ams_system, mock_zitadel, settings):
    _ = ams_system
    user = User.objects.create(email="acc@clet.gov.gh", status="pre_active",
                               zitadel_user_id="100000000000000009")
    Invitation.objects.create(email="acc@clet.gov.gh", system_code="ams", user=user,
                              zitadel_user_id="100000000000000009", status="pending",
                              lookup_token_hash=_TEST_LOOKUP_HASH)
    from rest_framework.test import APIClient
    client = APIClient()
    resp = client.post(
        "/v1/onboarding/accept",
        {"lookup_token": _TEST_LOOKUP_TOKEN, "code": "RESETCODE", "password": "Test1234!",
         "first_name": "Jane", "last_name": "Doe"},
        format="json",
        HTTP_X_INTERNAL_SECRET=settings.ONBOARDING_INTERNAL_SECRET,
    )
    assert resp.status_code == 200, resp.content
    user.refresh_from_db()
    assert user.status == "active"
    assert user.first_name == "Jane"
    assert user.last_name == "Doe"
    mock_zitadel.set_password_with_code.assert_called_once_with(
        "100000000000000009", "RESETCODE", "Test1234!"
    )


def test_accept_invitation_requires_first_name(ams_system, mock_zitadel, settings):
    _ = ams_system
    user = User.objects.create(email="acc@clet.gov.gh", status="pre_active",
                               zitadel_user_id="100000000000000009")
    Invitation.objects.create(email="acc@clet.gov.gh", system_code="ams", user=user,
                              zitadel_user_id="100000000000000009", status="pending",
                              lookup_token_hash=_TEST_LOOKUP_HASH)
    from rest_framework.test import APIClient
    client = APIClient()
    resp = client.post(
        "/v1/onboarding/accept",
        {"lookup_token": _TEST_LOOKUP_TOKEN, "code": "RESETCODE", "password": "Test1234!",
         "first_name": "", "last_name": "Doe"},
        format="json",
        HTTP_X_INTERNAL_SECRET=settings.ONBOARDING_INTERNAL_SECRET,
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "first_name and last_name are required"


def test_accept_invitation_requires_last_name(ams_system, mock_zitadel, settings):
    _ = ams_system
    user = User.objects.create(email="acc@clet.gov.gh", status="pre_active",
                               zitadel_user_id="100000000000000009")
    Invitation.objects.create(email="acc@clet.gov.gh", system_code="ams", user=user,
                              zitadel_user_id="100000000000000009", status="pending",
                              lookup_token_hash=_TEST_LOOKUP_HASH)
    from rest_framework.test import APIClient
    client = APIClient()
    resp = client.post(
        "/v1/onboarding/accept",
        {"lookup_token": _TEST_LOOKUP_TOKEN, "code": "RESETCODE", "password": "Test1234!",
         "first_name": "Jane", "last_name": ""},
        format="json",
        HTTP_X_INTERNAL_SECRET=settings.ONBOARDING_INTERNAL_SECRET,
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "first_name and last_name are required"


def test_accept_invitation_repairs_missing_role_binding(ams_system, mock_zitadel, settings):
    _, user_role, _ = ams_system
    user = User.objects.create(
        email="repair@clet.gov.gh",
        status="pre_active",
        zitadel_user_id="100000000000000010",
    )
    _repair_token = "repair-lookup-token"
    _repair_hash = hashlib.sha256(_repair_token.encode()).hexdigest()
    Invitation.objects.create(
        email="repair@clet.gov.gh",
        system_code="ams",
        user=user,
        zitadel_user_id="100000000000000010",
        role_ids=[str(user_role.id)],
        status="pending",
        lookup_token_hash=_repair_hash,
    )

    from rest_framework.test import APIClient

    client = APIClient()
    resp = client.post(
        "/v1/onboarding/accept",
        {"lookup_token": _repair_token, "code": "RESETCODE", "password": "Test1234!",
         "first_name": "Jane", "last_name": "Doe"},
        format="json",
        HTTP_X_INTERNAL_SECRET=settings.ONBOARDING_INTERNAL_SECRET,
    )

    assert resp.status_code == 200, resp.content
    assert RoleBinding.objects.filter(user=user, role=user_role, state="approved").exists()
    mock_zitadel.upsert_user_grant.assert_called_with(
        "100000000000000010",
        "proj-ams",
        ["user"],
    )


def test_accept_rejects_bad_secret():
    from rest_framework.test import APIClient
    client = APIClient()
    resp = client.post(
        "/v1/onboarding/accept",
        {"zitadel_user_id": "1", "code": "x", "password": "y", "first_name": "Jane", "last_name": "Doe"},
        format="json",
        HTTP_X_INTERNAL_SECRET="wrong",
    )
    assert resp.status_code == 403
