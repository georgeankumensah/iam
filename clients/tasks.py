import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("iam.clients.tasks")


@shared_task
def rotate_due_client_secrets() -> dict:
    """Rotate client secrets that are due for 180-day rotation.

    Respects a 14-day overlap window: clients whose ``secret_rotated_at`` is
    older than 166 days (180 − 14 overlap) get rotated.
    """
    from core.zitadel import zitadel

    from .models import OIDCClient

    cutoff = timezone.now() - timezone.timedelta(days=166)
    rotated = 0
    failed = 0

    clients = OIDCClient.objects.filter(
        lifecycle_state__in=["production_live", "sandbox_validated"],
        secret_rotated_at__lt=cutoff,
    ) | OIDCClient.objects.filter(
        lifecycle_state__in=["production_live", "sandbox_validated"],
        secret_rotated_at__isnull=True,
    )

    for client in clients:
        if not client.zitadel_app_id:
            continue
        try:
            zitadel().rotate_app_secret(str(client.zitadel_app_id))
            client.secret_rotated_at = timezone.now()
            client.save(update_fields=["secret_rotated_at"])
            rotated += 1
            logger.info("Rotated secret for client %s", client.client_id)
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to rotate secret for %s: %s", client.client_id, e)
            failed += 1

    return {"rotated": rotated, "failed": failed}
