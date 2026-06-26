import logging

from celery import shared_task
from django.utils import timezone

from audit.emit import emit_event

logger = logging.getLogger("iam.rbac.tasks")


@shared_task
def execute_overdue_access_review_revocations() -> dict:
    """Enforce REVOKE decisions past the 5-business-day SLA grace period.

    Items decided as ``revoke`` or ``change_role`` that are still pending
    enforcement after 5 business days are force-applied.
    """
    from .models import AccessReviewItem, RoleBinding

    cutoff = timezone.now() - timezone.timedelta(days=7)
    overdue = AccessReviewItem.objects.filter(
        decision__in=[AccessReviewItem.Decision.REVOKE, AccessReviewItem.Decision.CHANGE_ROLE],
        decided_at__lt=cutoff,
        binding__state=RoleBinding.BindingState.APPROVED,
    ).select_related("binding", "user")

    revoked = 0
    for item in overdue:
        if not item.binding:
            continue
        item.binding.state = RoleBinding.BindingState.REVOKED
        item.binding.save(update_fields=["state", "updated_at"])

        emit_event(
            actor_user_id=str(item.reviewer.id) if item.reviewer else "system",
            action="access_review.overdue_revocation",
            entity_type="role_binding",
            entity_id=str(item.binding.id),
            channel="system",
            result="success",
        )
        revoked += 1

    logger.info("Force-revoked %d overdue access-review items", revoked)
    return {"revoked": revoked}
