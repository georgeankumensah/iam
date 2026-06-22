import logging
from dataclasses import dataclass

import requests
from django.conf import settings
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger("iam.login.zitadel")

MFA_FACTOR_TOTP = "totp"
MFA_FACTOR_WEBAUTHN = "webauthn"
MFA_FACTOR_SMS = "sms"


@dataclass
class ZitadelAuthResult:
    success: bool
    session_id: str | None = None
    redirect_url: str | None = None
    mfa_required: bool = False
    mfa_factors: list[str] | None = None
    consent_required: bool = False
    error: str | None = None
    error_description: str | None = None


class ZitadelAuthService:
    def __init__(self) -> None:
        self.base_url = settings.ZITADEL_HOST.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def _post(self, path: str, data: dict | None = None) -> requests.Response:
        url = f"{self.base_url}{path}"
        resp = self.session.post(url, json=data or {}, timeout=15)
        resp.raise_for_status()
        return resp

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def _get(self, path: str, params: dict | None = None) -> requests.Response:
        url = f"{self.base_url}{path}"
        resp = self.session.get(url, params=params, timeout=15)
        resp.raise_for_status()
        return resp

    def verify_password(self, user_id: str, password: str) -> ZitadelAuthResult:
        try:
            resp = self._post(f"/auth/v1/users/{user_id}/verify_password", {"password": password})
            data = resp.json()
            return ZitadelAuthResult(success=True, session_id=data.get("sessionId"))
        except requests.HTTPError as e:
            status = e.response.status_code if e.response else 500
            if status == 401:
                return ZitadelAuthResult(success=False, error="invalid_credentials", error_description="Invalid email or password")
            logger.error("Zitadel verify_password failed: %s", e)
            return ZitadelAuthResult(success=False, error="server_error", error_description="Authentication service unavailable")
        except requests.RequestException as e:
            logger.error("Zitadel verify_password network error: %s", e)
            return ZitadelAuthResult(success=False, error="server_error", error_description="Authentication service unavailable")

    def create_session(self, user_id: str, auth_request_id: str) -> ZitadelAuthResult:
        try:
            resp = self._post("/auth/v1/sessions", {
                "userId": user_id,
                "authRequestId": auth_request_id,
            })
            data = resp.json()
            return ZitadelAuthResult(
                success=True,
                session_id=data.get("sessionId"),
                mfa_required=data.get("mfaRequired", False),
                mfa_factors=data.get("mfaFactors"),
                consent_required=data.get("consentRequired", False),
            )
        except requests.RequestException as e:
            logger.error("Zitadel create_session failed: %s", e)
            return ZitadelAuthResult(success=False, error="server_error")

    def verify_totp(self, session_id: str, code: str) -> ZitadelAuthResult:
        try:
            self._post(f"/auth/v1/sessions/{session_id}/verify/totp", {"code": code})
            return ZitadelAuthResult(success=True, session_id=session_id)
        except requests.HTTPError as e:
            if e.response and e.response.status_code == 401:
                return ZitadelAuthResult(success=False, error="invalid_mfa", error_description="Invalid verification code")
            return ZitadelAuthResult(success=False, error="server_error")
        except requests.RequestException as e:
            logger.error("Zitadel verify_totp failed: %s", e)
            return ZitadelAuthResult(success=False, error="server_error")

    def verify_webauthn(self, session_id: str, credential: dict) -> ZitadelAuthResult:
        try:
            self._post(f"/auth/v1/sessions/{session_id}/verify/webauthn", credential)
            return ZitadelAuthResult(success=True, session_id=session_id)
        except requests.RequestException as e:
            logger.error("Zitadel verify_webauthn failed: %s", e)
            return ZitadelAuthResult(success=False, error="server_error")

    def verify_sms(self, session_id: str, code: str) -> ZitadelAuthResult:
        try:
            self._post(f"/auth/v1/sessions/{session_id}/verify/sms", {"code": code})
            return ZitadelAuthResult(success=True, session_id=session_id)
        except requests.HTTPError as e:
            if e.response and e.response.status_code == 401:
                return ZitadelAuthResult(success=False, error="invalid_mfa", error_description="Invalid SMS code")
            return ZitadelAuthResult(success=False, error="server_error")
        except requests.RequestException as e:
            logger.error("Zitadel verify_sms failed: %s", e)
            return ZitadelAuthResult(success=False, error="server_error")

    def grant_consent(self, auth_request_id: str, approve: bool = True) -> ZitadelAuthResult:
        try:
            resp = self._post(f"/oauth/v2/consent/{auth_request_id}", {"granted": approve})
            data = resp.json()
            return ZitadelAuthResult(success=True, redirect_url=data.get("redirectUri"))
        except requests.RequestException as e:
            logger.error("Zitadel grant_consent failed: %s", e)
            return ZitadelAuthResult(success=False, error="server_error")

    def trigger_password_reset(self, email: str) -> ZitadelAuthResult:
        try:
            self._post("/management/v1/users/reset_password", {"email": email})
            return ZitadelAuthResult(success=True)
        except requests.RequestException as e:
            logger.error("Zitadel trigger_password_reset failed: %s", e)
            return ZitadelAuthResult(success=False, error="server_error")

    def get_user_by_email(self, email: str) -> dict | None:
        try:
            resp = self._get("/auth/v1/users", {"email": email})
            users = resp.json().get("users", [])
            return users[0] if users else None
        except requests.RequestException:
            return None
