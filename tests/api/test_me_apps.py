import pytest

from clients.models import OIDCClient
from rbac.models import Role, RoleBinding

pytestmark = pytest.mark.django_db


def test_me_includes_roles(admin_client, admin_user):
    OIDCClient.objects.create(client_id="c-ams", system_code="ams", name="AMS",
                              zitadel_project_id="p", redirect_uris=["http://localhost:5173/x"])
    role = Role.objects.create(system_code="ams", role_id="user", name="User")
    RoleBinding.objects.create(role=role, user=admin_user, state="approved")
    resp = admin_client.get("/v1/me")
    assert resp.status_code == 200
    roles = resp.json()["data"]["roles"]
    assert {"system_code": "ams", "role_id": "user", "is_admin": False} in roles


def test_me_patch_updates_phone(admin_client, admin_user):
    resp = admin_client.patch("/v1/me", {"phone": "+233200000000"}, format="json")
    assert resp.status_code == 200
    admin_user.refresh_from_db()
    assert admin_user.phone == "+233200000000"


def test_my_apps_returns_granted_systems(admin_client, admin_user):
    OIDCClient.objects.create(client_id="c-ams", system_code="ams", name="AMS",
                              zitadel_project_id="p",
                              redirect_uris=["http://localhost:5173/login/callback"])
    role = Role.objects.create(system_code="ams", role_id="user", name="User")
    RoleBinding.objects.create(role=role, user=admin_user, state="approved")
    resp = admin_client.get("/v1/me/apps")
    assert resp.status_code == 200
    body = resp.json()
    assert body["message"] == "Available systems retrieved."
    apps = body["data"]
    ams = next(a for a in apps if a["system_code"] == "ams")
    assert ams["frontend_url"] == "http://localhost:5173"
    assert ams["role"] == "user"
    assert ams["permissions"] == []
    assert ams["system_name"] == "AMS"


def test_my_sessions_empty_when_no_zitadel_user(admin_client):
    resp = admin_client.get("/v1/me/sessions")
    assert resp.status_code == 200
    assert resp.json()["data"] == []
