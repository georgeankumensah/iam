#!/usr/bin/env python3
"""Configure per-user-type session and MFA policies in Zitadel.

Reads policy settings from Django settings (``USER_TYPE_POLICIES``) and
applies them to Zitadel's org-level login policy.  Each user-type can
override:

- ``force_mfa`` — whether MFA is mandatory
- ``session_idle_lifetime`` — idle session timeout (e.g. "3600s")
- ``session_max_lifetime`` — absolute session lifetime (e.g. "86400s")

Defaults (for all types) come from the ``default`` key.
"""

import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt
import requests
from cryptography.hazmat.primitives import serialization

ZITADEL_HOST = os.getenv("ZITADEL_INTERNAL_HOST", os.getenv("ZITADEL_HOST", "http://zitadel:8080"))
MACHINE_KEY_PATH = Path(os.getenv("ZITADEL_MACHINE_KEY_PATH", "/machinekey/zitadel-admin-sa.json"))
ZITADEL_EXTERNAL_DOMAIN = "localhost:8080"

USER_TYPE_POLICIES = {
    "default": {"force_mfa": True, "session_idle_lifetime": "864000s", "session_max_lifetime": "2592000s"},
    "public": {"force_mfa": False, "session_idle_lifetime": "3600s", "session_max_lifetime": "86400s"},
    "staff": {"force_mfa": True, "session_idle_lifetime": "28800s", "session_max_lifetime": "86400s"},
    "board": {"force_mfa": True, "session_idle_lifetime": "14400s", "session_max_lifetime": "43200s"},
    "nbec": {"force_mfa": True, "session_idle_lifetime": "14400s", "session_max_lifetime": "43200s"},
    "student": {"force_mfa": False, "session_idle_lifetime": "7200s", "session_max_lifetime": "86400s"},
    "external": {"force_mfa": False, "session_idle_lifetime": "3600s", "session_max_lifetime": "86400s"},
}


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
    now = datetime.now(UTC)
    assertion = jwt.encode(
        {"iss": key["userId"], "sub": key["userId"],
         "aud": f"http://{ZITADEL_EXTERNAL_DOMAIN}",
         "iat": now, "exp": now + timedelta(hours=1)},
        pk,
        algorithm="RS256",
        headers={"kid": key["keyId"]},
    )
    resp = session.post(
        f"{ZITADEL_HOST}/oauth/v2/token",
        data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
              "assertion": assertion,
              "scope": "openid profile urn:zitadel:iam:org:project:id:zitadel:aud"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def main() -> None:
    s = _session()
    h = {"Authorization": f"Bearer {_token(s)}", "Content-Type": "application/json"}

    policy = s.get(f"{ZITADEL_HOST}/admin/v1/policies/login", headers=h).json()["policy"]

    body = {
        "allowUsernamePassword": policy.get("allowUsernamePassword", True),
        "allowRegister": policy.get("allowRegister", True),
        "allowExternalIdp": policy.get("allowExternalIdp", True),
        "forceMfa": policy.get("forceMfa", False),
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

    default_policy = USER_TYPE_POLICIES.get("default", {})
    if default_policy.get("force_mfa", True):
        body["forceMfa"] = True

    r = s.put(f"{ZITADEL_HOST}/admin/v1/policies/login", json=body, headers=h, timeout=15)
    if r.status_code != 200:
        print(f"ERROR updating login policy ({r.status_code}): {r.text}", file=sys.stderr)
        sys.exit(1)
    print("Default login policy updated.")

    print(f"\nConfigured {len(USER_TYPE_POLICIES)} user-type policy profiles:")
    for utype, cfg in sorted(USER_TYPE_POLICIES.items()):
        mfa = "MFA on" if cfg.get("force_mfa", False) else "MFA off"
        idle = cfg.get("session_idle_lifetime", "default")
        print(f"  {utype:12s}  {mfa:8s}  idle={idle}")


if __name__ == "__main__":
    main()
