import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("iam.delegation.tasks")


@shared_task
def expire_delegations():
    from .models import Delegation

    now = timezone.now()
    expired = Delegation.objects.filter(state=Delegation.DelegationState.ACTIVE, end_at__lte=now)
    count = 0
    for delegation in expired:
        delegation.state = Delegation.DelegationState.EXPIRED
        delegation.save(update_fields=["state"])
        count += 1
        logger.info("Delegation %s expired", delegation.id)

    return f"Expired {count} delegations"


@shared_task
def notify_dg_24h_before_expiry() -> dict:
    """Log delegation entries whose expiry is within the next 24 hours so a
    downstream notification process (e.g. System 21 comms) can pick them up.

    The audit event serves as the trigger for the notification pipeline.
    """
    from audit.emit import emit_event

    from .models import Delegation

    now = timezone.now()
    window_end = now + timezone.timedelta(hours=24)
    notified = 0

    due = Delegation.objects.filter(
        state=Delegation.DelegationState.ACTIVE,
        end_at__gt=now,
        end_at__lte=window_end,
    ).select_related("delegator", "delegate")

    for d in due:
        emit_event(
            actor_user_id=str(d.delegator.id),
            actor_email=d.delegator.email,
            action="delegation.about_to_expire",
            entity_type="delegation",
            entity_id=str(d.id),
            channel="delegation",
            result="success",
            metadata={
                "delegate_email": d.delegate.email,
                "role_id": d.role.role_id if d.role else "",
                "expires_at": d.end_at.isoformat(),
            },
        )
        notified += 1

    if notified:
        logger.info("Notified for %d delegation(s) expiring within 24 h", notified)
    return {"notified": notified}
