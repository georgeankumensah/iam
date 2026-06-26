import logging

import requests
from django.conf import settings

logger = logging.getLogger("iam.core.vault")


class VaultError(RuntimeError):
    pass


def _api_url() -> str:
    return getattr(settings, "PAM_VAULT_ADDR", "").strip()


def _token() -> str:
    return getattr(settings, "PAM_VAULT_TOKEN", "").strip()


def _post(path: str, json: dict) -> dict:
    base = _api_url()
    headers = {"X-Vault-Token": _token()}
    try:
        resp = requests.post(f"{base.rstrip('/')}/{path.lstrip('/')}", json=json, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json() if resp.content else {}
    except requests.RequestException as exc:
        raise VaultError(str(exc)) from exc


def lease_credentials(*, user_id: str, target_id: str, ttl_hours: int = 1) -> str:
    url = _api_url()
    if not url:
        logger.info("Vault not configured — skipping credential lease")
        return ""
    resp = _post(
        "v1/iam/pam/lease",
        json={"user_id": user_id, "target_id": target_id, "ttl": f"{ttl_hours}h"},
    )
    lease_id = str(resp.get("lease_id") or resp.get("data", {}).get("lease_id") or "")
    logger.info("Leased Vault credentials: lease_id=%s", lease_id)
    return lease_id


def revoke_lease(lease_id: str) -> None:
    url = _api_url()
    if not url or not lease_id:
        return
    _post("v1/sys/leases/revoke", json={"lease_id": lease_id})
    logger.info("Revoked Vault lease: %s", lease_id)
