import hashlib
import json
import logging

logger = logging.getLogger("iam.audit.chain")


def compute_hash_chain_ref(previous_hash: str, canonical_event: dict) -> str:
    raw = json.dumps(canonical_event, sort_keys=True, default=str)
    return hashlib.sha256(f"{previous_hash}{raw}".encode()).hexdigest()


def anchor_event(event) -> str:
    from .models import AuditChainAnchor

    last_anchor = AuditChainAnchor.objects.order_by("-id").first()
    previous_hash = last_anchor.hash_chain_ref if last_anchor else "0" * 64

    canonical = {
        "id": event.id,
        "timestamp": event.timestamp.isoformat(),
        "actor_user_id": str(event.actor_user_id),
        "action": event.action,
        "entity_type": event.entity_type,
        "entity_id": event.entity_id,
        "result": event.result,
        "channel": event.channel,
        "correlation_id": event.correlation_id,
    }

    chain_ref = compute_hash_chain_ref(previous_hash, canonical)

    AuditChainAnchor.objects.create(
        event_id=event.id,
        hash_chain_ref=chain_ref,
        previous_hash=previous_hash,
    )

    return chain_ref


def verify_chain(from_id: int = 0) -> list[dict]:
    from .models import AuditChainAnchor

    anchors = AuditChainAnchor.objects.filter(event_id__gte=from_id).order_by("event_id")
    failures: list[dict] = []
    prev_hash = "0" * 64

    for anchor in anchors:
        if anchor.previous_hash != prev_hash:
            failures.append({
                "event_id": anchor.event_id,
                "expected_prev": prev_hash,
                "actual_prev": anchor.previous_hash,
            })
        prev_hash = anchor.hash_chain_ref

    return failures
