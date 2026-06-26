"""Celery task module for the audit app.

Celery's ``autodiscover_tasks()`` only imports ``<app>.tasks``. ``forward_outbox``
lives in ``audit.forwarder``, so re-import it here to ensure it registers.
"""

import logging

from celery import shared_task
from django.utils import timezone

from .chain import verify_chain
from .emit import emit_event
from .forwarder import forward_outbox

logger = logging.getLogger("iam.audit.tasks")

__all__ = ["forward_outbox", "anchor_chain_daily", "cleanup_expired_active_sessions"]


@shared_task
def anchor_chain_daily() -> dict:
    """Create a daily anchor event and verify chain integrity.

    Produces a ``chain.daily_anchor`` audit event that serves as the daily
    root hash.  Also runs ``verify_chain`` and logs any failures.
    """
    event_id = emit_event(
        actor_user_id="00000000-0000-0000-0000-000000000000",
        actor_email="system@iam.clet.gov.gh",
        action="chain.daily_anchor",
        entity_type="audit_chain",
        entity_id=f"daily-{timezone.now().strftime('%Y-%m-%d')}",
        channel="system",
        result="success",
    )

    failures = verify_chain()
    if failures:
        logger.error("Chain integrity failures on daily anchor: %s", failures)

    return {
        "anchor_event_id": event_id,
        "failures": len(failures),
        "anchored_at": timezone.now().isoformat(),
    }


@shared_task
def cleanup_expired_active_sessions() -> int:
    """Mark expired, non-revoked ActiveSession records as revoked."""
    from .models import ActiveSession

    now = timezone.now()
    count = ActiveSession.objects.filter(
        revoked=False,
        expires_at__lt=now,
    ).update(revoked=True)
    if count:
        logger.info("Revoked %d expired ActiveSession(s)", count)
    return count
