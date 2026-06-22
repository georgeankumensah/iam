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
