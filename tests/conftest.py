
from unittest.mock import MagicMock

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture(autouse=True)
def mock_zitadel(monkeypatch):
    """Replace the ZITADEL service singleton so tests never hit the network.
    Returns the mock so individual tests can configure/assert calls."""
    m = MagicMock(name="ZitadelService")
    m.find_user_by_email.return_value = None
    m.create_human_user.return_value = "100000000000000001"
    m.get_or_create_project.return_value = "proj-1"
    m.find_project_by_name.return_value = "proj-1"
    m.create_spa_app.return_value = {"clientId": "client-1", "appId": "app-1"}
    m.find_app_by_name.return_value = None
    m.ensure_project_role.return_value = None
    m.upsert_user_grant.return_value = "grant-1"
    m.find_user_grant.return_value = {"id": "grant-1", "roleKeys": []}
    m.list_user_grants.return_value = []
    m.list_user_sessions.return_value = []
    m.request_password_set.return_value = "RESETCODE"
    m.set_password_with_code.return_value = None
    monkeypatch.setattr("core.zitadel._service", m)
    return m


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def admin_user() -> User:
    user = User.objects.create_user(
        email="admin@clet.gov.gh",
        user_type="staff",
        status="active",
        is_staff=True,
        is_superuser=True,
    )
    return user


@pytest.fixture
def staff_user() -> User:
    user = User.objects.create_user(
        email="staff@clet.gov.gh",
        user_type="staff",
        status="active",
    )
    return user


@pytest.fixture
def student_user() -> User:
    user = User.objects.create_user(
        email="student@edu.clet.gov.gh",
        user_type="student",
        status="active",
    )
    return user


@pytest.fixture
def auth_client(api_client: APIClient, staff_user: User) -> APIClient:
    api_client.force_authenticate(user=staff_user)
    return api_client


@pytest.fixture
def admin_client(api_client: APIClient, admin_user: User) -> APIClient:
    api_client.force_authenticate(user=admin_user)
    return api_client
