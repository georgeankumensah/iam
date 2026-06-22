import logging

import requests
from django.conf import settings

logger = logging.getLogger("iam.lifecycle.scim")


class UserProvisionerBackend:
    def __init__(self) -> None:
        self.base_url = settings.ZITADEL_HOST.rstrip("/")
        self.service_jwt = settings.ZITADEL_SERVICE_ACCOUNT_JWT
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.service_jwt}",
        })

    def create_user(self, email: str, first_name: str, last_name: str, **extra) -> dict | None:
        try:
            resp = self.session.post(
                f"{self.base_url}/management/v1/users/human",
                json={
                    "email": {"email": email, "isVerified": False},
                    "profile": {"firstName": first_name, "lastName": last_name},
                    **extra,
                },
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.error("Failed to create Zitadel user: %s", e)
            return None

    def update_user(self, user_id: str, **updates) -> bool:
        try:
            resp = self.session.put(
                f"{self.base_url}/management/v1/users/{user_id}",
                json=updates,
                timeout=15,
            )
            resp.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.error("Failed to update Zitadel user %s: %s", user_id, e)
            return False

    def deactivate_user(self, user_id: str) -> bool:
        try:
            resp = self.session.post(
                f"{self.base_url}/management/v1/users/{user_id}/deactivate",
                timeout=15,
            )
            resp.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.error("Failed to deactivate Zitadel user %s: %s", user_id, e)
            return False

    def terminate_sessions(self, user_id: str) -> bool:
        try:
            resp = self.session.delete(
                f"{self.base_url}/management/v1/users/{user_id}/sessions",
                timeout=15,
            )
            resp.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.error("Failed to terminate sessions for %s: %s", user_id, e)
            return False
