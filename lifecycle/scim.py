import logging

from core.zitadel import zitadel

logger = logging.getLogger("iam.lifecycle.scim")


class UserProvisionerBackend:
    """Provisions/deprovisions users in ZITADEL for SCIM + HRMS flows.

    Delegates to the shared core.zitadel client (correct JWT-bearer auth + Host
    header). The previous implementation passed the raw service-account key as a
    bearer token and never authenticated.
    """

    def __init__(self) -> None:
        self.z = zitadel()

    def create_user(self, email: str, first_name: str, last_name: str, **extra) -> dict | None:
        try:
            existing = self.z.find_user_by_email(email)
            if existing:
                return {"userId": existing["userId"]}
            return {"userId": self.z.create_human_user(email, first_name, last_name)}
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to create ZITADEL user: %s", e)
            return None

    def deactivate_user(self, user_id: str) -> bool:
        try:
            self.z.deactivate_user(user_id)
            return True
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to deactivate ZITADEL user %s: %s", user_id, e)
            return False

    def terminate_sessions(self, user_id: str) -> bool:
        try:
            self.z.terminate_user_sessions(user_id)
            return True
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to terminate sessions for %s: %s", user_id, e)
            return False
