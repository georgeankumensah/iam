from django.test import TestCase
from rest_framework import status

from core.exceptions import (
    AuthzDeniedError,
    MFARequiredError,
    RoleConflictError,
    StepUpRequiredError,
)


class ExceptionTests(TestCase):
    def test_authz_denied(self) -> None:
        exc = AuthzDeniedError()
        self.assertEqual(exc.code, "AUTHZ_DENIED")
        self.assertEqual(exc.status_code, status.HTTP_403_FORBIDDEN)

    def test_mfa_required(self) -> None:
        exc = MFARequiredError()
        self.assertEqual(exc.code, "MFA_REQUIRED")
        self.assertEqual(exc.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_step_up_required(self) -> None:
        exc = StepUpRequiredError()
        self.assertEqual(exc.code, "STEP_UP_REQUIRED")
        self.assertEqual(exc.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_role_conflict(self) -> None:
        exc = RoleConflictError()
        self.assertEqual(exc.code, "ROLE_CONFLICT")
        self.assertEqual(exc.status_code, status.HTTP_409_CONFLICT)

    def test_custom_message(self) -> None:
        exc = AuthzDeniedError(message="Custom denied message")
        self.assertEqual(exc.message, "Custom denied message")
