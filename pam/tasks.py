import logging

from celery import shared_task
from django.utils import timezone

from audit.emit import emit_event

logger = logging.getLogger("iam.pam.tasks")


@shared_task
def anchor_recording_hashes_daily() -> dict:
    """Anchors all PAM session recording SHA-256 hashes to the audit chain.

    Produces one audit event with the Merkle root of all active recording hashes.
    """
    import hashlib

    from .models import PamSession

    sessions = PamSession.objects.filter(
        status=PamSession.SessionStatus.ENDED,
        recording_sha256__gt="",
    )
    hashes = sorted(sessions.values_list("recording_sha256", flat=True))
    if not hashes:
        logger.info("No PAM recording hashes to anchor")
        return {"anchored_count": 0}

    combined = "".join(hashes).encode()
    root_hash = hashlib.sha256(combined).hexdigest()

    emit_event(
        actor_user_id="00000000-0000-0000-0000-000000000000",
        actor_email="system@iam.clet.gov.gh",
        action="pam.recording_hash_anchor",
        entity_type="pam_recording_root",
        entity_id=f"root-{timezone.now().strftime('%Y-%m-%d')}",
        channel="pam",
        result="success",
        metadata={
            "root_hash": root_hash,
            "session_count": len(hashes),
            "hashes": hashes,
        },
    )

    logger.info("Anchored %d recording hash(es) — root=%s", len(hashes), root_hash)
    return {"anchored_count": len(hashes), "root_hash": root_hash}


@shared_task
def cleanup_stale_pam_sessions() -> dict:
    """Mark PAM sessions that have been active > 24 hours as stale (ended).

    Long-running active sessions with no explicit end are considered stale.
    """
    from .models import PamSession

    cutoff = timezone.now() - timezone.timedelta(hours=24)
    stale_count = 0

    stale = PamSession.objects.filter(
        status=PamSession.SessionStatus.ACTIVE,
        started_at__lt=cutoff,
    )
    for session in stale:
        session.status = PamSession.SessionStatus.ENDED
        session.ended_at = timezone.now()
        session.save(update_fields=["status", "ended_at"])
        stale_count += 1

    logger.info("Marked %d stale PAM session(s) as ended", stale_count)
    return {"stale_sessions_ended": stale_count}
