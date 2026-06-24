#!/usr/bin/env python3
"""Configure Zitadel's default login policy for mandatory MFA.

Run after bootstrap (idempotent):

    docker compose exec django python scripts/configure_mfa.py

- Turns on `forceMfa` so every interactive login must complete a second factor.
- Ensures the available second factors include TOTP, U2F, OTP-Email and OTP-SMS.
- Leaves passkeys (multi-factor U2F with verification) enabled.

Note: OTP-SMS requires an SMS provider and OTP-Email requires SMTP to be
configured in Zitadel; without them those factors are offered but cannot send
codes. TOTP and WebAuthn work with no external dependency.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import requests
from cryptography.hazmat.primitives import serialization

ZITADEL_HOST = os.getenv("ZITADEL_INTERNAL_HOST", os.getenv("ZITADEL_HOST", "http://zitadel:8080"))
MACHINE_KEY_PATH = Path(os.getenv("ZITADEL_MACHINE_KEY_PATH", "/machinekey/zitadel-admin-sa.json"))
ZITADEL_EXTERNAL_DOMAIN = "localhost:8080"


class _HostHeaderAdapter(requests.adapters.HTTPAdapter):
    def __init__(self, host_header: str, **kwargs):
        self._host = host_header
        super().__init__(**kwargs)

    def add_headers(self, request, **kwargs):
        request.headers["Host"] = self._host


def _session() -> requests.Session:
    s = requests.Session()
    s.mount("http://", _HostHeaderAdapter(ZITADEL_EXTERNAL_DOMAIN))
    s.mount("https://", _HostHeaderAdapter(ZITADEL_EXTERNAL_DOMAIN))
    return s


def _token(session: requests.Session) -> str:
    key = json.loads(MACHINE_KEY_PATH.read_text())
    pk = serialization.load_pem_private_key(key["key"].encode(), password=None)
    now = datetime.now(timezone.utc)
    assertion = jwt.encode(
        {
            "iss": key["userId"],
            "sub": key["userId"],
            "aud": f"http://{ZITADEL_EXTERNAL_DOMAIN}",
            "iat": now,
            "exp": now + timedelta(hours=1),
        },
        pk,
        algorithm="RS256",
        headers={"kid": key["keyId"]},
    )
    resp = session.post(
        f"{ZITADEL_HOST}/oauth/v2/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
            "scope": "openid profile urn:zitadel:iam:org:project:id:zitadel:aud",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def main() -> None:
    s = _session()
    h = {"Authorization": f"Bearer {_token(s)}", "Content-Type": "application/json"}

    policy = s.get(f"{ZITADEL_HOST}/admin/v1/policies/login", headers=h).json()["policy"]

    # Update the default login policy with forceMfa enabled, preserving the
    # other existing values.
    body = {
        "allowUsernamePassword": policy.get("allowUsernamePassword", True),
        "allowRegister": policy.get("allowRegister", True),
        "allowExternalIdp": policy.get("allowExternalIdp", True),
        "forceMfa": True,
        "forceMfaLocalOnly": policy.get("forceMfaLocalOnly", False),
        "passwordlessType": policy.get("passwordlessType", "PASSWORDLESS_TYPE_ALLOWED"),
        "hidePasswordReset": policy.get("hidePasswordReset", False),
        "ignoreUnknownUsernames": policy.get("ignoreUnknownUsernames", False),
        "allowDomainDiscovery": policy.get("allowDomainDiscovery", True),
        "disableLoginWithEmail": policy.get("disableLoginWithEmail", False),
        "disableLoginWithPhone": policy.get("disableLoginWithPhone", False),
        "passwordCheckLifetime": policy.get("passwordCheckLifetime", "864000s"),
        "externalLoginCheckLifetime": policy.get("externalLoginCheckLifetime", "864000s"),
        "mfaInitSkipLifetime": policy.get("mfaInitSkipLifetime", "2592000s"),
        "secondFactorCheckLifetime": policy.get("secondFactorCheckLifetime", "64800s"),
        "multiFactorCheckLifetime": policy.get("multiFactorCheckLifetime", "43200s"),
    }
    r = s.put(f"{ZITADEL_HOST}/admin/v1/policies/login", json=body, headers=h, timeout=15)
    if r.status_code != 200:
        print(f"ERROR updating login policy ({r.status_code}): {r.text}", file=sys.stderr)
        sys.exit(1)
    print("forceMfa enabled on default login policy.")

    # Ensure the second factors we support are all present.
    for factor in ["SECOND_FACTOR_TYPE_OTP", "SECOND_FACTOR_TYPE_U2F",
                   "SECOND_FACTOR_TYPE_OTP_EMAIL", "SECOND_FACTOR_TYPE_OTP_SMS"]:
        r = s.post(
            f"{ZITADEL_HOST}/admin/v1/policies/login/second_factors",
            json={"type": factor},
            headers=h,
            timeout=15,
        )
        if r.status_code == 200:
            print(f"  added second factor {factor}")
        elif r.status_code == 409:
            print(f"  second factor {factor} already enabled")
        else:
            print(f"  WARN could not add {factor} ({r.status_code}): {r.text[:120]}")

    print("MFA configuration complete.")


if __name__ == "__main__":
    main()
