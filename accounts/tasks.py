import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("iam.accounts.tasks")


@shared_task
def expire_invitations() -> int:
    """Mark pending invitations past their expiry as expired."""
    from accounts.models import Invitation

    count = Invitation.objects.filter(
        status=Invitation.Status.PENDING,
        expires_at__lt=timezone.now(),
    ).update(status=Invitation.Status.EXPIRED, updated_at=timezone.now())
    if count:
        logger.info("Expired %d invitation(s)", count)
    return count
