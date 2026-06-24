from django.test import TestCase, override_settings


class LoginEndpointTests(TestCase):
    @override_settings(DEBUG=True)
    def test_login_page_redirects_to_spa(self) -> None:
        resp = self.client.get("/login/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("localhost:5173/login", resp["Location"])

    @override_settings(DEBUG=True)
    def test_login_page_with_auth_request_redirects(self) -> None:
        resp = self.client.get("/login/?authRequest=test-123")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("authRequest=test-123", resp["Location"])

    @override_settings(DEBUG=True)
    def test_password_reset_page_redirects(self) -> None:
        resp = self.client.get("/login/password-reset")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("localhost:5173/login/password-reset", resp["Location"])

    @override_settings(DEBUG=True)
    def test_error_page_redirects(self) -> None:
        resp = self.client.get("/login/error?error=test_error&error_description=Test+error")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("localhost:5173/login/error", resp["Location"])

    @override_settings(DEBUG=True)
    def test_consent_page_redirects(self) -> None:
        resp = self.client.get("/login/consent?authRequest=test-123")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("localhost:5173/login/consent", resp["Location"])

    @override_settings(DEBUG=False)
    def test_login_page_returns_404_when_spa_not_built(self) -> None:
        resp = self.client.get("/login/")
        self.assertEqual(resp.status_code, 404)
