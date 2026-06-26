import base64
import json
import sys
from datetime import UTC, datetime, timedelta

import jwt
import requests
from cryptography.hazmat.primitives import serialization

ZITADEL_HOST = "http://zitadel:8080"
ZITADEL_EXTERNAL_DOMAIN = "localhost:8080"
MACHINE_KEY_PATH = "/machinekey/zitadel-admin-sa.json"


class _HostHeaderAdapter(requests.adapters.HTTPAdapter):
    def __init__(self, host_header, **kwargs):
        self._host = host_header
        super().__init__(**kwargs)

    def add_headers(self, request, **kwargs):
        request.headers["Host"] = self._host


def session():
    s = requests.Session()
    s.mount("http://", _HostHeaderAdapter(ZITADEL_EXTERNAL_DOMAIN))
    s.mount("https://", _HostHeaderAdapter(ZITADEL_EXTERNAL_DOMAIN))
    return s


with open(MACHINE_KEY_PATH) as f:
    key_data = json.load(f)

private_key = serialization.load_pem_private_key(key_data["key"].encode(), password=None)
now = datetime.now(UTC)
payload = {
    "iss": key_data["userId"],
    "sub": key_data["userId"],
    "aud": f"http://{ZITADEL_EXTERNAL_DOMAIN}",
    "iat": now,
    "exp": now + timedelta(hours=1),
}
assertion = jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": key_data["keyId"]})
resp = session().post(
    f"{ZITADEL_HOST}/oauth/v2/token",
    data={
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": assertion,
        "scope": "openid profile urn:zitadel:iam:org:project:id:zitadel:aud",
    },
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    timeout=15,
)
token = resp.json()["access_token"]

org_id = session().get(f"{ZITADEL_HOST}/management/v1/orgs/me", headers={"Authorization": f"Bearer {token}"}, timeout=15).json()["org"]["id"]
print(f"Org ID: {org_id}")

resp = session().post(f"{ZITADEL_HOST}/management/v1/projects/_search",
    json={"query": {"offset": "0", "limit": 100, "asc": True}},
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, timeout=15)
projects = resp.json().get("result", [])
print("Projects found:", [f"{p['id']}:{p['name']}" for p in projects])
project_id = None
for p in projects:
    if p["name"] == "IAM 3.0":
        project_id = p["id"]
        break
if not project_id:
    sys.exit(1)
print(f"Project ID: {project_id}")

resp = session().post(f"{ZITADEL_HOST}/management/v1/projects/{project_id}/apps/_search",
    json={"query": {"offset": "0", "limit": 100, "asc": True}},
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, timeout=15)
apps = resp.json().get("result", [])
client_ids = {}
for a in apps:
    cid = a.get("clientId") or a.get("id", "?")
    name = a.get("appName") or a.get("name", "?")
    client_ids[name] = cid
    print(f"  App: {name} clientId={cid}")

resp = session().post(
    f"{ZITADEL_HOST}/management/v1/users/_search",
    json={
        "query": {"offset": "0", "limit": 100, "asc": True},
        "queries": [{"userNameQuery": {"userName": "iam-backend", "method": "USER_NAME_QUERY_METHOD_EQUALS"}}],
    },
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    timeout=15,
)
users = resp.json().get("result", [])
sa_user_id = users[0]["id"]
print(f"iam-backend user ID: {sa_user_id}")

resp = session().post(
    f"{ZITADEL_HOST}/management/v1/users/{sa_user_id}/keys",
    json={"type": "KEY_TYPE_JSON", "expirationDate": (datetime.now(UTC) + timedelta(days=365)).isoformat()},
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    timeout=15,
)
key_details_b64 = resp.json().get("keyDetails", "")
sa_key_json = base64.b64decode(key_details_b64).decode()

print()
print("=== ADD THESE TO .env ===")
print(f"ZITADEL_PROJECT_ID={project_id}")
print(f"ZITADEL_ORG_ID={org_id}")
print(f"ZITADEL_SERVICE_ACCOUNT_JWT={sa_key_json}")
print(f"OIDC_RP_CLIENT_ID={client_ids.get('IAM SPA', '')}")
print(f"AMS_CLIENT_ID={client_ids.get('AMS', '')}")
print(f"NBES_CLIENT_ID={client_ids.get('NBES', '')}")
