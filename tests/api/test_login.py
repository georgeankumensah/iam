from django.test import TestCase


class LoginEndpointTests(TestCase):
    def test_login_page_renders(self) -> None:
        resp = self.client.get("/login/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Sign In")

    def test_login_page_with_auth_request(self) -> None:
        resp = self.client.get("/login/?authRequest=test-123")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "test-123")

    def test_password_reset_page_renders(self) -> None:
        resp = self.client.get("/login/password-reset")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Reset Password")

    def test_error_page(self) -> None:
        resp = self.client.get("/login/error?error=test_error&error_description=Test+error")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Test error")

    def test_consent_page_renders(self) -> None:
        resp = self.client.get("/login/consent?authRequest=test-123")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Authorize Application")
