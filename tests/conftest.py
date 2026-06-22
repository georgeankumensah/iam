
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


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
