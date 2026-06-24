import pytest

from accounts.models import User
from clients.models import OIDCClient
from rbac.models import Role, RoleBinding

pytestmark = pytest.mark.django_db


@pytest.fixture
def system_and_roles():
    OIDCClient.objects.create(client_id="c-ams", system_code="ams", name="AMS",
                              zitadel_project_id="proj-ams", zitadel_app_id="app-ams")
    user_role = Role.objects.create(system_code="ams", role_id="user", name="User")
    admin_role = Role.objects.create(system_code="ams", role_id="admin", name="Admin", is_admin=True)
    return user_role, admin_role


@pytest.fixture
def member():
    return User.objects.create(email="m@clet.gov.gh", status="active",
                               zitadel_user_id="100000000000000010")


def test_bind_and_user_roles(admin_client, system_and_roles, member, mock_zitadel):
    user_role, _ = system_and_roles
    resp = admin_client.post(f"/v1/admin/roles/{user_role.id}/bind",
                             {"user_id": str(member.id)}, format="json")
    assert resp.status_code == 201, resp.content
    mock_zitadel.upsert_user_grant.assert_called()

    roles = admin_client.get(f"/v1/admin/users/{member.id}/roles").json()["data"]
    assert any(r["role_id"] == "user" and r["state"] == "approved" for r in roles)


def test_unbind_revokes(admin_client, system_and_roles, member, mock_zitadel):
    user_role, _ = system_and_roles
    RoleBinding.objects.create(role=user_role, user=member, state="approved")
    resp = admin_client.post(f"/v1/admin/roles/{user_role.id}/unbind",
                             {"user_id": str(member.id)}, format="json")
    assert resp.status_code == 200
    assert RoleBinding.objects.get(role=user_role, user=member).state == "revoked"


def test_dg_queue_and_approve(admin_client, system_and_roles, member, mock_zitadel):
    _, admin_role = system_and_roles
    b = RoleBinding.objects.create(role=admin_role, user=member, state="requested")
    queue = admin_client.get("/v1/admin/role-bindings").json()["data"]
    assert any(item["id"] == str(b.id) for item in queue)

    resp = admin_client.post(f"/v1/admin/role-bindings/{b.id}/approve", {}, format="json")
    assert resp.status_code == 200
    b.refresh_from_db()
    assert b.state == "approved"
    mock_zitadel.upsert_user_grant.assert_called()


def test_dg_reject(admin_client, system_and_roles, member):
    _, admin_role = system_and_roles
    b = RoleBinding.objects.create(role=admin_role, user=member, state="requested")
    resp = admin_client.post(f"/v1/admin/role-bindings/{b.id}/reject", {}, format="json")
    assert resp.status_code == 200
    b.refresh_from_db()
    assert b.state == "revoked"
