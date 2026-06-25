import pytest

from clients.models import OIDCClient
from rbac.models import Role

pytestmark = pytest.mark.django_db


@pytest.fixture
def system():
    return OIDCClient.objects.create(
        client_id="client-ams", system_code="ams", name="AMS",
        zitadel_project_id="proj-ams", zitadel_app_id="app-ams",
        redirect_uris=["http://localhost:5173/login/callback"],
    )


def test_systems_list(admin_client, system):
    Role.objects.create(system_code="ams", role_id="user", name="AMS User")
    resp = admin_client.get("/v1/admin/systems")
    assert resp.status_code == 200
    data = resp.json()["data"]
    ams = next(s for s in data if s["system_code"] == "ams")
    assert ams["client_id"] == "client-ams"
    assert any(r["role_id"] == "user" for r in ams["roles"])


def test_add_system_role(admin_client, system, mock_zitadel):
    resp = admin_client.post(
        "/v1/admin/systems/ams/roles",
        {"role_id": "inspector", "name": "Inspector", "is_admin": False},
        format="json",
    )
    assert resp.status_code == 201, resp.content
    assert Role.objects.filter(system_code="ams", role_id="inspector").exists()
    mock_zitadel.ensure_project_role.assert_called()


def test_deprecate_system_role(admin_client, system, mock_zitadel):
    Role.objects.create(system_code="ams", role_id="temp", name="Temp")
    resp = admin_client.delete("/v1/admin/systems/ams/roles/temp")
    assert resp.status_code == 200
    assert Role.objects.get(system_code="ams", role_id="temp").is_deprecated is True
    mock_zitadel.remove_project_role.assert_called()


def test_toggle_role_check(admin_client, system, mock_zitadel):
    resp = admin_client.post("/v1/admin/systems/ams/role-check", {"enabled": False}, format="json")
    assert resp.status_code == 200
    assert resp.json()["data"]["role_check"] is False
    mock_zitadel.set_project_role_check.assert_called_with("proj-ams", False)


def test_suspend_and_activate_client(admin_client, system, mock_zitadel):
    r1 = admin_client.post(f"/v1/admin/clients/{system.id}/suspend", {}, format="json")
    assert r1.status_code == 200
    system.refresh_from_db()
    assert system.lifecycle_state == "suspended"
    mock_zitadel.deactivate_app.assert_called()

    r2 = admin_client.post(f"/v1/admin/clients/{system.id}/activate", {}, format="json")
    assert r2.status_code == 200
    system.refresh_from_db()
    assert system.lifecycle_state == "production_live"


def test_create_system_via_api(admin_client, mock_zitadel):
    resp = admin_client.post(
        "/v1/admin/clients",
        {"system_code": "xyz", "name": "XYZ", "frontend_port": 5190,
         "roles": [{"role_id": "admin", "name": "Admin", "is_admin": True}]},
        format="json",
    )
    assert resp.status_code == 201, resp.content
    assert OIDCClient.objects.filter(system_code="xyz").exists()
    assert Role.objects.filter(system_code="xyz", role_id="admin", is_admin=True).exists()
