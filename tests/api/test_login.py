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
