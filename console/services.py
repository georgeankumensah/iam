import csv
import io
import logging
from typing import Any

logger = logging.getLogger("iam.console.services")


def create_user_in_zitadel(email: str) -> dict | None:
    from lifecycle.scim import UserProvisionerBackend

    backend = UserProvisionerBackend()
    result = backend.create_user(email=email, first_name="", last_name="")
    return result


def deactivate_user_in_zitadel(zitadel_user_id: str) -> bool:
    from lifecycle.scim import UserProvisionerBackend

    backend = UserProvisionerBackend()
    return backend.deactivate_user(zitadel_user_id)


def reactivate_user_in_zitadel(zitadel_user_id: str) -> bool:
    from lifecycle.scim import UserProvisionerBackend

    backend = UserProvisionerBackend()
    return backend.reactivate_user(zitadel_user_id)


def parse_bulk_csv(csv_content: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(csv_content))
    users = []
    for row in reader:
        users.append({
            "email": row.get("email", ""),
            "user_type": row.get("user_type", "external"),
            # Optional onboarding columns: invite into a system with a role.
            "system_code": (row.get("system_code", "") or "").strip(),
            "role": (row.get("role", "") or "").strip(),
            "metadata": {
                "first_name": row.get("first_name", ""),
                "last_name": row.get("last_name", ""),
            },
        })
    return users
