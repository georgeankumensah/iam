import base64
import json
from unittest.mock import MagicMock

from django.test import TestCase, override_settings

# The Django login/ app now redirects to the Next.js login-app (Login V2) on
# port 3000, which hosts the custom login/MFA/consent UI.
LOGIN_APP = "localhost:3000"


class LoginEndpointTests(TestCase):
    @override_settings(DEBUG=True)
    def test_login_page_redirects_to_login_app(self) -> None:
        resp = self.client.get("/login/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn(f"{LOGIN_APP}/login", resp["Location"])

    @override_settings(DEBUG=True)
    def test_login_page_with_auth_request_redirects(self) -> None:
        resp = self.client.get("/login/?authRequest=test-123")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("authRequest=test-123", resp["Location"])

    @override_settings(DEBUG=True)
    def test_password_reset_page_redirects(self) -> None:
        resp = self.client.get("/login/password-reset")
        self.assertEqual(resp.status_code, 302)
        self.assertIn(f"{LOGIN_APP}/login/password-reset", resp["Location"])

    @override_settings(DEBUG=True)
    def test_error_page_redirects(self) -> None:
        resp = self.client.get("/login/error?error=test_error&error_description=Test+error")
        self.assertEqual(resp.status_code, 302)
        self.assertIn(f"{LOGIN_APP}/login/error", resp["Location"])

    @override_settings(DEBUG=True)
    def test_consent_page_redirects(self) -> None:
        resp = self.client.get("/login/consent?authRequest=test-123")
        self.assertEqual(resp.status_code, 302)
        self.assertIn(f"{LOGIN_APP}/login/consent", resp["Location"])

    @override_settings(LOGIN_APP_BASE_URL="http://localhost:3000")
    def test_complete_without_session_redirects_to_login(self) -> None:
        resp = self.client.get("/login/complete?authRequest=test-123")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "http://localhost:3000/login?authRequest=test-123")

    def test_complete_uses_django_zitadel_client(self) -> None:
        from core import zitadel as zitadel_module

        mock_zitadel = MagicMock()
        mock_zitadel.create_oidc_callback.return_value = "http://localhost:5173/login/callback?code=abc&state=xyz"
        original = zitadel_module._service
        zitadel_module._service = mock_zitadel
        try:
            cookie = base64.b64encode(
                json.dumps({"id": "session-1", "token": "token-1", "userId": "user-1"}).encode()
            ).decode()
            self.client.cookies["zitadel-session"] = cookie
            resp = self.client.get("/login/complete?authRequest=test-123")
        finally:
            zitadel_module._service = original

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "http://localhost:5173/login/callback?code=abc&state=xyz")
        mock_zitadel.create_oidc_callback.assert_called_once_with("test-123", "session-1", "token-1")

    def test_complete_retries_after_syncing_stale_grants(self) -> None:
        from accounts.models import User
        from clients.models import OIDCClient
        from core import zitadel as zitadel_module
        from core.zitadel import ZitadelError
        from rbac.models import Role, RoleBinding

        OIDCClient.objects.create(
            client_id="client-ams",
            system_code="ams",
            name="AMS",
            zitadel_project_id="proj-ams",
            redirect_uris=["http://localhost:5173/login/callback"],
        )
        user = User.objects.create(email="ams@clet.gov.gh", status="active", zitadel_user_id="user-1")
        role = Role.objects.create(system_code="ams", role_id="institution_contact", name="Institution Contact")
        RoleBinding.objects.create(user=user, role=role, state=RoleBinding.BindingState.APPROVED)

        mock_zitadel = MagicMock()
        mock_zitadel.create_oidc_callback.side_effect = [
            ZitadelError(403, "Errors.User.GrantRequired"),
            "http://localhost:5173/login/callback?code=abc&state=xyz",
        ]
        mock_zitadel.upsert_user_grant.return_value = "grant-1"
        mock_zitadel.find_user_grant.return_value = None
        original = zitadel_module._service
        zitadel_module._service = mock_zitadel
        try:
            cookie = base64.b64encode(
                json.dumps({"id": "session-1", "token": "token-1", "userId": "user-1"}).encode()
            ).decode()
            self.client.cookies["zitadel-session"] = cookie
            resp = self.client.get("/login/complete?authRequest=test-123")
        finally:
            zitadel_module._service = original

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "http://localhost:5173/login/callback?code=abc&state=xyz")
        mock_zitadel.upsert_user_grant.assert_called_with("user-1", "proj-ams", ["institution_contact"])
