#!/usr/bin/env python3
"""Configure a JWT IdP in Zitadel for Keycloak authentication via the login-app.

Creates a JWT IdP in Zitadel that points to the login-app's /api/auth/jwt
endpoint as the JWT issuer. The login-app authenticates against Keycloak
server-side, generates a signed JWT, and proxies it to Zitadel for validation.

Usage:

    docker compose exec django python scripts/configure_jwt_idp.py

Or (local):

    source .venv/bin/activate
    python scripts/configure_jwt_idp.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django
django.setup()

from django.conf import settings
from core.zitadel import ZitadelError, zitadel

IDP_NAME = "Keycloak (JWT)"
JWT_ENDPOINT = "http://login-app:3000/api/auth/jwt"
JWT_ISSUER = "iam-login-app"
JWT_HEADER_NAME = "x-custom-tkn"
JWKS_ENDPOINT = "http://login-app:3000/api/auth/jwks"


def main():
    z = zitadel()

    print(f"Creating JWT IdP: {IDP_NAME}")
    print(f"  JWT Endpoint: {JWT_ENDPOINT}")
    print(f"  Issuer:       {JWT_ISSUER}")
    print(f"  JWKS:         {JWKS_ENDPOINT}")

    body = {
        "name": IDP_NAME,
        "type": "IDP_TYPE_JWT",
        "jwtConfig": {
            "jwtEndpoint": JWT_ENDPOINT,
            "issuer": JWT_ISSUER,
            "keysEndpoint": JWKS_ENDPOINT,
            "headerName": JWT_HEADER_NAME,
        },
        "autoRegister": True,
        "autoUpdate": True,
        "autoLinking": "IDP_AUTO_LINKING_OPTION_USERNAME",
        "isCreationAllowed": True,
        "isLinkingAllowed": True,
    }

    try:
        data = z.request("POST", "/v2/idps", body)
        idp_id = data.get("id", "")
        print(f"  IdP created: {idp_id}")
    except ZitadelError as e:
        if e.status == 409:
            print("  IdP already exists (skipping)")
            return
        print(f"  ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    login_policy = z.request("GET", "/admin/v1/policies/login").get("policy", {})
    existing_idps = login_policy.get("idps", [])

    if idp_id not in [i.get("idpId") for i in existing_idps]:
        print("  Adding IdP to the default login policy...")
        try:
            z.request(
                "POST",
                "/admin/v1/policies/login/idps",
                {"idpId": idp_id},
            )
            print("  IdP added to login policy.")
        except ZitadelError as e:
            print(f"  WARN: could not add IdP to policy ({e.status}): {e.body[:120]}")

    print()
    print("=== Next steps ===")
    print(f"Set NEXT_PUBLIC_KEYCLOAK_IDP_ID={idp_id} in login-app/.env")
    print("Restart login-app for the env var to take effect.")
    print("Done.")


if __name__ == "__main__":
    main()
