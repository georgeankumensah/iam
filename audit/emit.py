import logging
from typing import Any

from .chain import anchor_event

logger = logging.getLogger("iam.audit")


def emit_event(
    actor_user_id: str,
    action: str,
    entity_type: str = "",
    entity_id: str = "",
    channel: str = "console",
    result: str = "success",
    correlation_id: str = "",
    ip_address: str | None = None,
    user_agent: str = "",
    actor_email: str = "",
    client_id: str = "",
    metadata: dict[str, Any] | None = None,
) -> int | None:
    from .models import AuditEvent

    event = AuditEvent.objects.create(
        actor_user_id=actor_user_id,
        actor_email=actor_email,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        ip_address=ip_address,
        user_agent=user_agent,
        channel=channel,
        client_id=client_id,
        correlation_id=correlation_id,
        result=result,
        redacted_metadata=metadata or {},
    )

    try:
        chain_ref = anchor_event(event)
        event.hash_chain_ref = chain_ref
        event.save(update_fields=["hash_chain_ref"])
    except Exception as e:
        logger.error("Failed to anchor audit event %s: %s", event.id, e)

    return event.id
