"""Celery task module for the audit app.
    Celery's ``autodiscover_tasks()`` only imports ``<app>.tasks``. ``forward_outbox``
    lives in ``audit.forwarder``, so re-import it here to ensure it registers.
"""

from .forwarder import forward_outbox

__all__ = ["forward_outbox"]
