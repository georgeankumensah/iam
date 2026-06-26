#!/usr/bin/env python3
"""Point ZITADEL's SMTP provider at the dev Mailpit container and activate it.

Run after the stack is up (idempotent-ish; adds a config and activates it):

    docker compose exec django python scripts/configure_smtp.py

Mailpit captures all outbound mail; view invite/reset emails at
http://localhost:8025. Swap the host/credentials for a real provider in prod.
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
DOMAIN = "localhost:8080"

SMTP_HOST = os.getenv("SMTP_HOST", "mailpit:1025")
SENDER = os.getenv("SMTP_SENDER", "iam@clet.gov.gh")
SENDER_NAME = os.getenv("SMTP_SENDER_NAME", "CLET IAM")


class _HostHeaderAdapter(requests.adapters.HTTPAdapter):
    def __init__(self, host_header, **kwargs):
        self._host = host_header
        super().__init__(**kwargs)

    def add_headers(self, request, **kwargs):
        request.headers["Host"] = self._host


def _session():
    s = requests.Session()
    s.mount("http://", _HostHeaderAdapter(DOMAIN))
    s.mount("https://", _HostHeaderAdapter(DOMAIN))
    return s


def _token(s):
    key = json.loads(MACHINE_KEY_PATH.read_text())
    pk = serialization.load_pem_private_key(key["key"].encode(), password=None)
    now = datetime.now(UTC)
    a = jwt.encode(
        {"iss": key["userId"], "sub": key["userId"], "aud": f"http://{DOMAIN}",
         "iat": now, "exp": now + timedelta(hours=1)},
        pk, algorithm="RS256", headers={"kid": key["keyId"]},
    )
    r = s.post(f"{ZITADEL_HOST}/oauth/v2/token",
               data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": a,
                     "scope": "openid profile urn:zitadel:iam:org:project:id:zitadel:aud"},
               headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=15)
    r.raise_for_status()
    return r.json()["access_token"]


def main():
    s = _session()
    h = {"Authorization": f"Bearer {_token(s)}", "Content-Type": "application/json"}

    host, _, port = SMTP_HOST.partition(":")
    body = {
        "description": "Mailpit (dev)",
        "senderAddress": SENDER,
        "senderName": SENDER_NAME,
        "tls": False,
        "host": SMTP_HOST,
        "user": "",
        "password": "",
    }
    r = s.post(f"{ZITADEL_HOST}/admin/v1/smtp", json=body, headers=h, timeout=15)
    if r.status_code != 200:
        print(f"ERROR adding SMTP config ({r.status_code}): {r.text}", file=sys.stderr)
        sys.exit(1)
    smtp_id = r.json().get("id", "")
    print(f"Added SMTP config {smtp_id} → {SMTP_HOST}")

    if smtp_id:
        r = s.post(f"{ZITADEL_HOST}/admin/v1/smtp/{smtp_id}/_activate", json={}, headers=h, timeout=15)
        print(f"Activate: {r.status_code}")
    print("SMTP configured. View mail at http://localhost:8025")


if __name__ == "__main__":
    main()
