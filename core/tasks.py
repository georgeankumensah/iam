"""Celery tasks for periodic metric collection."""

import logging

from celery import shared_task

logger = logging.getLogger("iam.core.tasks")


@shared_task
def collect_db_connection_metrics() -> dict:
    """Update ``db_connection_count`` gauge from Django's connection pool."""
    from django.db import connection

    from .metrics import db_connection_count

    try:
        connection.ensure_connection()
        db_connection_count.set(1)
        return {"db_connected": True}
    except Exception as e:
        db_connection_count.set(0)
        logger.warning("DB connection check failed: %s", e)
        return {"db_connected": False, "error": str(e)}


@shared_task
def collect_pam_session_metrics() -> dict:
    """Update ``pam_session_count`` gauge with active PAM session count."""
    from pam.models import PamSession

    from .metrics import pam_session_count

    count = PamSession.objects.filter(status=PamSession.SessionStatus.ACTIVE).count()
    pam_session_count.set(count)
    return {"active_pam_sessions": count}
