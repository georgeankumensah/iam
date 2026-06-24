import json, os, sys, base64, time, jwt, requests
from datetime import datetime, timedelta, timezone
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
now = datetime.now(timezone.utc)
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

sa_user_id = key_data["userId"]
print(f"Admin SA user ID: {sa_user_id}")

# Find IAM 3.0 project
resp = session().post(f"{ZITADEL_HOST}/management/v1/projects/_search",
    json={"query": {"offset": "0", "limit": 100, "asc": True}},
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, timeout=15)
projects = resp.json().get("result", [])
iam_project = [p for p in projects if p["name"] == "IAM 3.0"][0]
pid = iam_project["id"]
print(f"IAM 3.0 project: {pid}")

# Grant admin SA PROJECT_OWNER on IAM 3.0
resp = session().post(f"{ZITADEL_HOST}/management/v1/projects/{pid}/members",
    json={"userId": sa_user_id, "roles": ["PROJECT_OWNER"]},
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, timeout=15)
if resp.status_code == 200:
    print("Granted PROJECT_OWNER to admin SA on IAM 3.0 project.")
elif resp.status_code == 409:
    print("Admin SA is already a project member.")
else:
    print(f"Failed ({resp.status_code}): {resp.text}")

# Also grant ORG_OWNER to admin SA
org_id = session().get(f"{ZITADEL_HOST}/management/v1/orgs/me", headers={"Authorization": f"Bearer {token}"}, timeout=15).json()["org"]["id"]
resp = session().post(f"{ZITADEL_HOST}/management/v1/orgs/{org_id}/members",
    json={"userId": sa_user_id, "roles": ["ORG_OWNER"]},
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, timeout=15)
if resp.status_code == 200:
    print("Granted ORG_OWNER to admin SA.")
elif resp.status_code == 409:
    print("Admin SA is already an org member.")
else:
    print(f"Failed ({resp.status_code}): {resp.text}")
