import logging

import requests
from django.conf import settings
from django.utils import timezone

from audit.emit import emit_event
from core.vault import VaultError, lease_credentials, revoke_lease

from .models import PamSession

logger = logging.getLogger("iam.pam.services")


class PamIntegrationError(RuntimeError):
    pass


def _jumpserver_api_url() -> str:
    return getattr(settings, "PAM_JUMPSERVER_API_URL", "").strip()


def _jumpserver_token() -> str:
    return getattr(settings, "PAM_JUMPSERVER_API_TOKEN", "").strip()


def _post(url: str, *, json: dict, headers: dict | None = None) -> dict:
    headers = headers or {}
    try:
        resp = requests.post(url, json=json, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json() if resp.content else {}
    except requests.RequestException as exc:
        raise PamIntegrationError(str(exc)) from exc


def _open_jumpserver_session(*, user_id: str, target_id: str, vault_lease_id: str) -> dict:
    base = _jumpserver_api_url()
    if not base:
        return {}
    token = _jumpserver_token()
    headers = {"Authorization": f"Bearer {token}"}
    return _post(
        f"{base.rstrip('/')}/api/v1/iam/sessions",
        json={"user_id": user_id, "target_id": target_id, "vault_lease_id": vault_lease_id},
        headers=headers,
    )


def _revoke_jumpserver_session(session: PamSession) -> None:
    base = _jumpserver_api_url()
    if not base:
        return
    token = _jumpserver_token()
    headers = {"Authorization": f"Bearer {token}"}
    _post(
        f"{base.rstrip('/')}/api/v1/iam/sessions/{session.id}/revoke",
        json={"reason": "iam_revoke"},
        headers=headers,
    )


def list_pam_sessions(*, status: str = "") -> list[PamSession]:
    qs = PamSession.objects.select_related("user").order_by("-started_at")
    if status:
        qs = qs.filter(status=status)
    return list(qs)


def broker_pam_session(*, user, target_id: str, target_host: str = "", ttl_hours: int = 1) -> PamSession:
    ttl_hours = min(max(int(ttl_hours or 1), 1), 4)
    try:
        vault_lease_id = lease_credentials(
            user_id=str(user.zitadel_user_id or user.id),
            target_id=target_id,
            ttl_hours=ttl_hours,
        )
    except VaultError as e:
        logger.error("Vault lease failed for user %s target %s: %s", user.id, target_id, e)
        vault_lease_id = ""

    try:
        jump = _open_jumpserver_session(
            user_id=str(user.zitadel_user_id or user.id),
            target_id=target_id,
            vault_lease_id=vault_lease_id,
        )
    except PamIntegrationError as e:
        logger.error("JumpServer session failed for user %s target %s: %s", user.id, target_id, e)
        jump = {}

    session = PamSession.objects.create(
        user=user,
        target_id=target_id,
        target_host=target_host,
        vault_lease_id=vault_lease_id,
        recording_uri=jump.get("recording_uri", ""),
        recording_sha256=jump.get("recording_sha256", ""),
        started_at=timezone.now(),
    )

    emit_event(
        actor_user_id=str(user.id),
        actor_email=user.email,
        action="pam.session_brokered",
        entity_type="pam_session",
        entity_id=str(session.id),
        channel="pam",
        metadata={
            "target_id": target_id,
            "ttl_hours": ttl_hours,
            "vault_lease_id": vault_lease_id,
            "jumpserver_session": bool(jump),
        },
    )

    logger.info("Brokered PAM session %s for user %s target %s", session.id, user.id, target_id)
    return session


def revoke_pam_session(*, session: PamSession, actor_id: str = "system", reason: str = "") -> PamSession:
    if session.status != PamSession.SessionStatus.ACTIVE:
        return session

    try:
        _revoke_jumpserver_session(session)
    except PamIntegrationError as e:
        logger.warning("JumpServer revoke failed for session %s: %s", session.id, e)

    try:
        revoke_lease(session.vault_lease_id)
    except VaultError as e:
        logger.warning("Vault lease revoke failed for session %s: %s", session.id, e)

    session.status = PamSession.SessionStatus.REVOKED
    session.ended_at = timezone.now()
    session.save(update_fields=["status", "ended_at"])

    emit_event(
        actor_user_id="00000000-0000-0000-0000-000000000000" if actor_id == "system" else actor_id,
        actor_email="",
        action="pam.session_revoked",
        entity_type="pam_session",
        entity_id=str(session.id),
        channel="pam",
        metadata={"reason": reason, "vault_lease_id": session.vault_lease_id, "actor_id": actor_id},
    )

    logger.info("Revoked PAM session %s (reason: %s)", session.id, reason)
    return session


def revoke_user_pam_sessions(*, user, reason: str = "leaver") -> int:
    active = PamSession.objects.filter(user=user, status=PamSession.SessionStatus.ACTIVE)
    count = 0
    for session in active:
        revoke_pam_session(session=session, actor_id=str(user.id), reason=reason)
        count += 1
    logger.info("Revoked %d active PAM session(s) for user %s (%s)", count, user.id, reason)
    return count
