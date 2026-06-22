import logging

import requests
from django.conf import settings
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger("iam.clients.zitadel")


class ZitadelClientManager:
    def __init__(self) -> None:
        self.base_url = settings.ZITADEL_HOST.rstrip("/")
        self.service_jwt = settings.ZITADEL_SERVICE_ACCOUNT_JWT
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.service_jwt}",
        })

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def create_project(self, name: str) -> dict:
        resp = self.session.post(f"{self.base_url}/management/v1/projects", json={"name": name}, timeout=15)
        resp.raise_for_status()
        return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def create_app(self, project_id: str, name: str, redirect_uris: list[str]) -> dict:
        resp = self.session.post(
            f"{self.base_url}/management/v1/projects/{project_id}/apps",
            json={
                "name": name,
                "redirectUris": redirect_uris,
                "responseTypes": ["OIDC_RESPONSE_TYPE_CODE"],
                "grantTypes": ["OIDC_GRANT_TYPE_AUTHORIZATION_CODE"],
                "appType": "OIDC_APP_TYPE_WEB",
                "authMethodType": "OIDC_AUTH_METHOD_TYPE_BASIC",
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def rotate_secret(self, project_id: str, app_id: str) -> dict:
        resp = self.session.put(
            f"{self.base_url}/management/v1/projects/{project_id}/apps/{app_id}/secret",
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def deactivate_app(self, project_id: str, app_id: str) -> dict:
        resp = self.session.post(
            f"{self.base_url}/management/v1/projects/{project_id}/apps/{app_id}/deactivate",
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
