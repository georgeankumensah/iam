import logging

import requests
from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("iam.audit.forwarder")

SYSTEM_22_AUDIT_URL = settings.SYSTEM_22_AUDIT_URL if hasattr(settings, "SYSTEM_22_AUDIT_URL") else ""


@shared_task
def forward_outbox():
    from .models import AuditOutbox

    if not SYSTEM_22_AUDIT_URL:
        logger.warning("SYSTEM_22_AUDIT_URL not configured, skipping outbox flush")
        return

    now = timezone.now()
    pending = AuditOutbox.objects.filter(
        delivered=False,
        next_retry_at__isnull=True,
    ) | AuditOutbox.objects.filter(
        delivered=False,
        next_retry_at__lte=now,
    )

    sent = 0
    for entry in pending:
        if entry.retry_count >= entry.max_retries:
            logger.error("Outbox entry %s max retries reached", entry.id)
            continue

        try:
            resp = requests.post(
                SYSTEM_22_AUDIT_URL,
                json={
                    "event_id": entry.event_id,
                    "action": entry.event.action,
                    "actor_user_id": str(entry.event.actor_user_id),
                    "timestamp": entry.event.timestamp.isoformat(),
                    "hash_chain_ref": entry.event.hash_chain_ref,
                },
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            resp.raise_for_status()
            entry.delivered = True
            entry.delivered_at = timezone.now()
            entry.save(update_fields=["delivered", "delivered_at"])
            sent += 1
        except requests.RequestException as e:
            entry.retry_count += 1
            entry.last_error = str(e)
            entry.next_retry_at = timezone.now() + timezone.timedelta(minutes=5 * entry.retry_count)
            entry.save(update_fields=["retry_count", "last_error", "next_retry_at"])

    return f"Forwarded {sent} events"
