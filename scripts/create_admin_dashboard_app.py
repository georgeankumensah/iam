"""Create the Admin Dashboard OIDC application in the existing local Zitadel.

Usage:
    docker compose exec django python scripts/create_admin_dashboard_app.py

Requires the machine key at /machinekey/zitadel-admin-sa.json (from bootstrap).
"""

import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt
import requests
from cryptography.hazmat.primitives import serialization

ZITADEL_HOST = os.getenv("ZITADEL_HOST", "http://zitadel:8080")
ISSUER = f"{ZITADEL_HOST.rstrip('/')}"
ZITADEL_EXTERNAL_DOMAIN = os.environ.get("ZITADEL_EXTERNAL_DOMAIN", "localhost:8080")


class _HostHeaderAdapter(requests.adapters.HTTPAdapter):
    def __init__(self, host_header: str, **kwargs):
        self._host = host_header
        super().__init__(**kwargs)

    def add_headers(self, request, **kwargs):
        request.headers["Host"] = self._host


def session():
    s = requests.Session()
    s.mount("http://", _HostHeaderAdapter(ZITADEL_EXTERNAL_DOMAIN))
    s.mount("https://", _HostHeaderAdapter(ZITADEL_EXTERNAL_DOMAIN))
    return s


def load_machine_key() -> dict:
    path = Path("/machinekey/zitadel-admin-sa.json")
    if not path.exists():
        print("Machine key not found. Run the full bootstrap first.", file=sys.stderr)
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


def get_access_token(key_data: dict) -> str:
    private_key = serialization.load_pem_private_key(
        key_data["key"].encode(), password=None
    )
    now = datetime.now(UTC)
    payload = {
        "iss": key_data["userId"],
        "sub": key_data["userId"],
        "aud": f"http://{ZITADEL_EXTERNAL_DOMAIN}",
        "iat": now,
        "exp": now + timedelta(hours=1),
    }
    assertion = jwt.encode(
        payload, private_key, algorithm="RS256", headers={"kid": key_data["keyId"]}
    )
    s = session()
    resp = s.post(
        f"{ISSUER}/oauth/v2/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
            "scope": "openid profile urn:zitadel:iam:org:project:id:zitadel:aud",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    if resp.status_code != 200:
        print(f"Token exchange failed ({resp.status_code}): {resp.text}", file=sys.stderr)
        sys.exit(1)
    return resp.json()["access_token"]


def find_project_id(token: str) -> str:
    s = session()
    resp = s.post(
        f"{ISSUER}/management/v1/projects/_search",
        json={
            "query": {"offset": "0", "limit": 100, "asc": True},
            "queries": [],
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=15,
    )
    if resp.status_code != 200:
        print(f"Failed to search projects ({resp.status_code}): {resp.text}", file=sys.stderr)
        sys.exit(1)
    result = resp.json().get("result", [])
    for project in result:
        if project["name"] == "IAM 3.0":
            project_id = project["id"]
            print(f"Found project: IAM 3.0  (id={project_id})")
            return project_id
    print("IAM 3.0 project not found. Run the full bootstrap first.", file=sys.stderr)
    sys.exit(1)


def create_admin_dashboard_app(token: str, project_id: str) -> str:
    s = session()
    # Check if Admin Dashboard app already exists
    resp = s.get(
        f"{ISSUER}/management/v1/projects/{project_id}/apps",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    if resp.status_code == 200:
        for app in resp.json().get("result", []):
            if app.get("appName") == "Admin Dashboard":
                client_id = app.get("clientId", "")
                print(f"Admin Dashboard app already exists  (client_id={client_id})")
                return client_id

    payload = {
        "name": "Admin Dashboard",
        "redirectUris": ["http://localhost:3001/auth/callback"],
        "postLogoutRedirectUris": ["http://localhost:3001/logout"],
        "responseTypes": ["OIDC_RESPONSE_TYPE_CODE"],
        "grantTypes": [
            "OIDC_GRANT_TYPE_AUTHORIZATION_CODE",
            "OIDC_GRANT_TYPE_REFRESH_TOKEN",
        ],
        "appType": "OIDC_APP_TYPE_USER_AGENT",
        "authMethodType": "OIDC_AUTH_METHOD_TYPE_NONE",
        "version": "OIDC_VERSION_1_0",
        "devMode": True,
        "accessTokenType": "OIDC_TOKEN_TYPE_JWT",
    }
    resp = s.post(
        f"{ISSUER}/management/v1/projects/{project_id}/apps/oidc",
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=15,
    )
    if resp.status_code != 200:
        print(f"Failed to create app ({resp.status_code}): {resp.text}", file=sys.stderr)
        sys.exit(1)
    client_id = resp.json().get("clientId", "")
    print(f"Created OIDC app: Admin Dashboard  (client_id={client_id})")
    return client_id


if __name__ == "__main__":
    key_data = load_machine_key()
    token = get_access_token(key_data)
    project_id = find_project_id(token)
    client_id = create_admin_dashboard_app(token, project_id)
    print()
    print("=" * 60)
    print("  Add to admin-dashboard/.env:")
    print("=" * 60)
    print(f"  VITE_OIDC_CLIENT_ID={client_id}")
    print("=" * 60)
