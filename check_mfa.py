import json
from datetime import UTC, datetime, timedelta

import jwt
import requests
from cryptography.hazmat.primitives import serialization

ZITADEL_HOST = "http://zitadel:8080"
ZITADEL_EXTERNAL_DOMAIN = "localhost:8080"

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

with open("/machinekey/zitadel-admin-sa.json") as f:
    key_data = json.load(f)

private_key = serialization.load_pem_private_key(key_data["key"].encode(), password=None)
now = datetime.now(UTC)
payload = {
    "iss": key_data["userId"], "sub": key_data["userId"],
    "aud": f"http://{ZITADEL_EXTERNAL_DOMAIN}",
    "iat": now, "exp": now + timedelta(hours=1),
}
assertion = jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": key_data["keyId"]})
resp = session().post(f"{ZITADEL_HOST}/oauth/v2/token",
    data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion, "scope": "openid profile urn:zitadel:iam:org:project:id:zitadel:aud"},
    headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=15)
token = resp.json()["access_token"]

# Find admin user
resp = session().post(f"{ZITADEL_HOST}/management/v1/users/_search",
    json={"query": {"offset": "0", "limit": 100, "asc": True}},
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, timeout=15)
users = resp.json().get("result", [])
for u in users:
    if u.get("userName", "").startswith("admin"):
        admin_id = u["id"]
        print(f"Admin user: {json.dumps(u, indent=2)}")
        break

# Check MFA for admin user
resp = session().get(f"{ZITADEL_HOST}/management/v1/users/{admin_id}/factors",
    headers={"Authorization": f"Bearer {token}"}, timeout=15)
print(f"\nMFA factors: {json.dumps(resp.json(), indent=2)}")
