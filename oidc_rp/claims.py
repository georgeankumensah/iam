from typing import Any


def map_claims_to_user(payload: dict[str, Any]) -> dict[str, Any]:
    claims = {
        "sub": payload.get("sub", ""),
        "email": payload.get("email", ""),
        "user_type": payload.get("user_type", "external"),
        "roles": payload.get("urn:zitadel:iam:org:project:roles", []),
        "portal_access": payload.get("portal_access", []),
        "permissions": payload.get("permissions", []),
    }
    return claims
