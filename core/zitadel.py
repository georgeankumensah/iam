"""Authenticated ZITADEL Management/v2 API client for Django.

Authenticates with the service-account machine key via the JWT-bearer grant and
sends the instance's external domain as the Host header so ZITADEL resolves the
correct instance. All Django apps that talk to ZITADEL should use this instead
of passing the raw key as a bearer token.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import requests
from cryptography.hazmat.primitives import serialization
from django.conf import settings

logger = logging.getLogger("iam.core.zitadel")


class ZitadelError(Exception):
    def __init__(self, status: int, body: str):
        self.status = status
        self.body = body
        super().__init__(f"ZITADEL API error {status}: {body[:300]}")


class _HostHeaderAdapter(requests.adapters.HTTPAdapter):
    def __init__(self, host_header: str, **kwargs):
        self._host = host_header
        super().__init__(**kwargs)

    def add_headers(self, request, **kwargs):
        request.headers["Host"] = self._host


class ZitadelService:
    def __init__(self) -> None:
        self.base_url = settings.ZITADEL_HOST.rstrip("/")
        self.domain = settings.ZITADEL_EXTERNAL_DOMAIN
        self.key_path = Path(settings.ZITADEL_MACHINE_KEY_PATH)
        self._token: str | None = None
        self._token_exp: float = 0.0
        self._lock = threading.Lock()
        self._session = requests.Session()
        self._session.mount("http://", _HostHeaderAdapter(self.domain))
        self._session.mount("https://", _HostHeaderAdapter(self.domain))

    # -- auth ---------------------------------------------------------------

    def _access_token(self) -> str:
        with self._lock:
            if self._token and time.time() < self._token_exp:
                return self._token
            key = json.loads(self.key_path.read_text())
            pk = serialization.load_pem_private_key(key["key"].encode(), password=None)
            now = datetime.now(timezone.utc)
            assertion = jwt.encode(
                {
                    "iss": key["userId"],
                    "sub": key["userId"],
                    "aud": f"http://{self.domain}",
                    "iat": now,
                    "exp": now + timedelta(hours=1),
                },
                pk,
                algorithm="RS256",
                headers={"kid": key["keyId"]},
            )
            resp = self._session.post(
                f"{self.base_url}/oauth/v2/token",
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": assertion,
                    "scope": "openid profile urn:zitadel:iam:org:project:id:zitadel:aud",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=15,
            )
            if resp.status_code != 200:
                raise ZitadelError(resp.status_code, resp.text)
            data = resp.json()
            self._token = data["access_token"]
            self._token_exp = time.time() + data.get("expires_in", 3600) - 60
            return self._token

    def request(self, method: str, path: str, json_body: dict | None = None) -> dict:
        resp = self._session.request(
            method,
            f"{self.base_url}{path}",
            json=json_body,
            headers={
                "Authorization": f"Bearer {self._access_token()}",
                "Content-Type": "application/json",
            },
            timeout=20,
        )
        if resp.status_code < 200 or resp.status_code >= 300:
            raise ZitadelError(resp.status_code, resp.text)
        return resp.json() if resp.content else {}

    # -- projects & apps ----------------------------------------------------

    def find_project_by_name(self, name: str) -> str | None:
        data = self.request(
            "POST", "/management/v1/projects/_search",
            {"query": {"offset": "0", "limit": "100", "asc": True}},
        )
        for p in data.get("result", []):
            if p.get("name") == name:
                return p["id"]
        return None

    def create_project(self, name: str) -> str:
        # Roles are asserted into tokens and access requires a role grant.
        data = self.request(
            "POST", "/management/v1/projects",
            {
                "name": name,
                "projectRoleAssertion": True,
                "projectRoleCheck": True,
                "hasProjectCheck": False,
            },
        )
        return data["id"]

    def get_or_create_project(self, name: str) -> str:
        return self.find_project_by_name(name) or self.create_project(name)

    def find_app_by_name(self, project_id: str, name: str) -> dict | None:
        data = self.request(
            "POST", f"/management/v1/projects/{project_id}/apps/_search",
            {"query": {"offset": "0", "limit": "100", "asc": True}},
        )
        for a in data.get("result", []):
            if a.get("name") == name:
                return a
        return None

    def create_spa_app(self, project_id: str, name: str, redirect_uris: list[str],
                       post_logout_uris: list[str]) -> dict:
        """Create a public PKCE SPA (user-agent) OIDC app. Returns {clientId, appId}."""
        data = self.request(
            "POST", f"/management/v1/projects/{project_id}/apps/oidc",
            {
                "name": name,
                "redirectUris": redirect_uris,
                "postLogoutRedirectUris": post_logout_uris,
                "responseTypes": ["OIDC_RESPONSE_TYPE_CODE"],
                "grantTypes": ["OIDC_GRANT_TYPE_AUTHORIZATION_CODE", "OIDC_GRANT_TYPE_REFRESH_TOKEN"],
                "appType": "OIDC_APP_TYPE_USER_AGENT",
                "authMethodType": "OIDC_AUTH_METHOD_TYPE_NONE",
                "version": "OIDC_VERSION_1_0",
                "devMode": True,
                "accessTokenType": "OIDC_TOKEN_TYPE_JWT",
                "accessTokenRoleAssertion": True,
                "idTokenRoleAssertion": True,
                "idTokenUserinfoAssertion": True,
            },
        )
        return {"clientId": data.get("clientId", ""), "appId": data.get("appId", "")}

    # -- roles --------------------------------------------------------------

    def list_project_roles(self, project_id: str) -> list[dict]:
        data = self.request(
            "POST", f"/management/v1/projects/{project_id}/roles/_search",
            {"query": {"offset": "0", "limit": "100", "asc": True}},
        )
        return data.get("result", [])

    def ensure_project_role(self, project_id: str, key: str, display: str, group: str = "") -> None:
        try:
            self.request(
                "POST", f"/management/v1/projects/{project_id}/roles",
                {"roleKey": key, "displayName": display, "group": group},
            )
        except ZitadelError as e:
            if e.status != 409:  # already exists
                raise

    def remove_project_role(self, project_id: str, key: str) -> None:
        try:
            self.request("DELETE", f"/management/v1/projects/{project_id}/roles/{key}")
        except ZitadelError as e:
            if e.status != 404:
                raise

    # -- user grants --------------------------------------------------------

    def create_user_grant(self, user_id: str, project_id: str, role_keys: list[str]) -> str:
        data = self.request(
            "POST", f"/management/v1/users/{user_id}/grants",
            {"projectId": project_id, "roleKeys": role_keys},
        )
        return data.get("userGrantId", "")

    def find_user_grant(self, user_id: str, project_id: str) -> dict | None:
        data = self.request(
            "POST", "/management/v1/users/grants/_search",
            {"queries": [
                {"userIdQuery": {"userId": user_id}},
                {"projectIdQuery": {"projectId": project_id}},
            ]},
        )
        result = data.get("result", [])
        return result[0] if result else None

    def set_user_grant_roles(self, user_id: str, grant_id: str, role_keys: list[str]) -> None:
        self.request(
            "PUT", f"/management/v1/users/{user_id}/grants/{grant_id}",
            {"roleKeys": role_keys},
        )

    def remove_user_grant(self, user_id: str, grant_id: str) -> None:
        try:
            self.request("DELETE", f"/management/v1/users/{user_id}/grants/{grant_id}")
        except ZitadelError as e:
            if e.status != 404:
                raise

    def upsert_user_grant(self, user_id: str, project_id: str, role_keys: list[str]) -> str:
        """Create the grant or update its role set if one already exists."""
        existing = self.find_user_grant(user_id, project_id)
        if existing:
            self.set_user_grant_roles(user_id, existing["id"], role_keys)
            return existing["id"]
        return self.create_user_grant(user_id, project_id, role_keys)

    # -- users --------------------------------------------------------------

    def find_user_by_email(self, email: str) -> dict | None:
        data = self.request(
            "POST", "/v2/users",
            {"query": {"offset": "0", "limit": "1"},
             "queries": [{"emailQuery": {"emailAddress": email}}]},
        )
        result = data.get("result", [])
        return result[0] if result else None

    def create_human_user(self, email: str, first_name: str, last_name: str) -> str:
        data = self.request(
            "POST", "/v2/users/human",
            {
                "username": email,
                "profile": {"givenName": first_name or email.split("@")[0], "familyName": last_name or "."},
                "email": {"email": email, "isVerified": False},
            },
        )
        return data["userId"]

    def request_password_set(self, user_id: str, url_template: str | None = None,
                             return_code: bool = False) -> str | None:
        """Issue a password-set (reset) code for onboarding.

        With return_code=True (dev) the code is returned; otherwise ZITADEL
        emails a link built from url_template (must contain {{.Code}} and
        {{.UserID}}). Unlike the invite code, this code is accepted directly by
        set_password_with_code so our custom acceptance page can set the initial
        password.
        """
        if return_code:
            body: dict = {"returnCode": {}}
        else:
            body = {"sendLink": {"notificationType": "NOTIFICATION_TYPE_Email"}}
            if url_template:
                body["sendLink"]["urlTemplate"] = url_template
        data = self.request("POST", f"/v2/users/{user_id}/password_reset", body)
        return data.get("verificationCode")

    def set_password_with_code(self, user_id: str, code: str, new_password: str) -> None:
        self.request(
            "POST", f"/v2/users/{user_id}/password",
            {"newPassword": {"password": new_password, "changeRequired": False},
             "verificationCode": code},
        )

    def list_user_grants(self, user_id: str) -> list[dict]:
        """All of a user's project grants (roleKeys per project)."""
        data = self.request(
            "POST", "/management/v1/users/grants/_search",
            {"queries": [{"userIdQuery": {"userId": user_id}}]},
        )
        return data.get("result", [])

    # -- app lifecycle ------------------------------------------------------

    def deactivate_app(self, project_id: str, app_id: str) -> None:
        self.request("POST", f"/management/v1/projects/{project_id}/apps/{app_id}/_deactivate", {})

    def reactivate_app(self, project_id: str, app_id: str) -> None:
        self.request("POST", f"/management/v1/projects/{project_id}/apps/{app_id}/_reactivate", {})

    def regenerate_app_secret(self, project_id: str, app_id: str) -> dict:
        return self.request("PUT", f"/management/v1/projects/{project_id}/apps/{app_id}/oidc_config/_generate_client_secret", {})

    def set_project_role_check(self, project_id: str, enabled: bool) -> None:
        """Toggle whether a role grant is required to enter the project's apps."""
        project = self.request("GET", f"/management/v1/projects/{project_id}").get("project", {})
        self.request(
            "PUT", f"/management/v1/projects/{project_id}",
            {
                "name": project.get("name"),
                "projectRoleAssertion": project.get("projectRoleAssertion", True),
                "projectRoleCheck": enabled,
                "hasProjectCheck": project.get("hasProjectCheck", False),
                "privateLabelingSetting": project.get(
                    "privateLabelingSetting", "PRIVATE_LABELING_SETTING_UNSPECIFIED"
                ),
            },
        )

    # -- sessions -----------------------------------------------------------

    def list_user_sessions(self, user_id: str) -> list[dict]:
        data = self.request(
            "POST", "/v2/sessions/search",
            {"queries": [{"userIdQuery": {"id": user_id}}]},
        )
        return data.get("sessions", [])

    def delete_session(self, session_id: str) -> None:
        try:
            self.request("DELETE", f"/v2/sessions/{session_id}")
        except ZitadelError as e:
            if e.status != 404:
                raise

    def terminate_user_sessions(self, user_id: str) -> None:
        # Re-evaluate access after a role change by ending the user's sessions.
        try:
            self.request("DELETE", f"/management/v1/users/{user_id}/sessions")
        except ZitadelError as e:
            if e.status not in (404, 400):
                raise


_service: ZitadelService | None = None


def zitadel() -> ZitadelService:
    global _service
    if _service is None:
        _service = ZitadelService()
    return _service
