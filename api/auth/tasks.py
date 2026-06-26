import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("iam.auth.tasks")


@shared_task
def cleanup_expired_auth_sessions() -> dict:
    """Revoke expired AuthSession and AuthState records."""
    from .models import AuthSession, AuthState

    now = timezone.now()

    session_count = AuthSession.objects.filter(
        is_revoked=False,
        expires_at__lt=now,
    ).update(is_revoked=True, revoked_at=now)

    state_count = AuthState.objects.filter(
        expires_at__lt=now,
    ).delete()[0]

    logger.info("Cleaned %d expired session(s) and %d expired state(s)", session_count, state_count)
    return {"expired_sessions_revoked": session_count, "expired_states_deleted": state_count}
