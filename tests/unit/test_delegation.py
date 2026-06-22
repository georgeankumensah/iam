from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from delegation.models import Delegation
from rbac.models import Role

User = get_user_model()


class DelegationModelTests(TestCase):
    def setUp(self) -> None:
        self.delegator = User.objects.create_user(email="delegator@test.gov", user_type="staff", status="active")
        self.delegate = User.objects.create_user(email="delegate@test.gov", user_type="staff", status="active")
        self.role = Role.objects.create(system_code="IAM", role_id="test-role", name="Test Role")

    def test_create_delegation(self) -> None:
        delegation = Delegation.objects.create(
            delegator=self.delegator,
            delegate=self.delegate,
            role=self.role,
            start_at=timezone.now(),
            end_at=timezone.now() + timedelta(days=7),
            justification="Test delegation",
        )
        self.assertEqual(delegation.state, Delegation.DelegationState.ACTIVE)
        self.assertEqual(str(delegation.delegator), str(self.delegator))

    def test_delegation_active_status(self) -> None:
        delegation = Delegation.objects.create(
            delegator=self.delegator,
            delegate=self.delegate,
            role=self.role,
            start_at=timezone.now(),
            end_at=timezone.now() + timedelta(days=7),
        )
        self.assertEqual(delegation.state, "active")

    def test_delegation_expiry(self) -> None:
        delegation = Delegation.objects.create(
            delegator=self.delegator,
            delegate=self.delegate,
            role=self.role,
            start_at=timezone.now() - timedelta(days=10),
            end_at=timezone.now() - timedelta(days=3),
        )
        delegation.state = Delegation.DelegationState.EXPIRED
        delegation.save()
        self.assertEqual(delegation.state, "expired")
