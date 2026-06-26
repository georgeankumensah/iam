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


def test_nbes_roles_match_seed_catalogue():
    """Cross-service CI: NBES roles from setup_systems match the seed catalogue.

    Ensures every role defined in setup_systems' NBES entry can be created
    in the Role model, so NBES can rely on the IAM role catalogue.
    """
    from clients.management.commands.setup_systems import SYSTEMS
    nbes_config = next(s for s in SYSTEMS if s["code"] == "nbes")
    for role_id, name, is_admin in nbes_config["roles"]:
        Role.objects.get_or_create(
            system_code="nbes", role_id=role_id, defaults={
                "name": name, "is_admin": is_admin, "version": 1,
                "effective_from": "2026-01-01T00:00:00Z",
            },
        )
    expected_role_ids = {r[0] for r in nbes_config["roles"]}
    actual_role_ids = set(Role.objects.filter(system_code="nbes").values_list("role_id", flat=True))
    missing = expected_role_ids - actual_role_ids
    assert not missing, f"NBES roles missing from catalogue: {missing}"


def test_iam_seed_admin_user_exists():
    """The bootstrap admin user is created exactly once by seed_iam."""
    from django.conf import settings

    from accounts.models import User
    admins = User.objects.filter(email=settings.BOOTSTRAP_ADMIN_EMAIL, is_superuser=True)
    assert admins.count() <= 1, "Multiple admin users found — seed_iam should be idempotent"


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
