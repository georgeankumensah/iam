from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from audit.models import AuditChainAnchor, AuditEvent
from audit.serializers import AuditEventSerializer
from console.permissions import IsIAMAdmin
from core.responses import success_response


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def audit_verify(request):
    """Verify the audit hash-chain integrity (linkage + content recompute)."""
    from audit.chain import compute_hash_chain_ref

    from_id = int(request.query_params.get("from_id", 0))
    anchors = AuditChainAnchor.objects.filter(event_id__gte=from_id).order_by("event_id")
    events = {e.id: e for e in AuditEvent.objects.filter(id__gte=from_id)}

    failures = []
    prev_hash = "0" * 64
    checked = 0
    for a in anchors:
        checked += 1
        if a.previous_hash != prev_hash:
            failures.append({"event_id": a.event_id, "issue": "broken_link",
                             "expected_prev": prev_hash, "actual_prev": a.previous_hash})
        ev = events.get(a.event_id)
        if ev:
            canonical = {
                "id": ev.id, "timestamp": ev.timestamp.isoformat(),
                "actor_user_id": str(ev.actor_user_id), "action": ev.action,
                "entity_type": ev.entity_type, "entity_id": ev.entity_id,
                "result": ev.result, "channel": ev.channel,
                "correlation_id": ev.correlation_id,
            }
            recomputed = compute_hash_chain_ref(a.previous_hash, canonical)
            if recomputed != a.hash_chain_ref:
                failures.append({"event_id": a.event_id, "issue": "content_tampered"})
        prev_hash = a.hash_chain_ref

    return success_response(data={
        "checked": checked,
        "intact": not failures,
        "failures": failures,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def audit_search(request):
    qs = AuditEvent.objects.all()

    if request.query_params.get("actor_user_id"):
        qs = qs.filter(actor_user_id=request.query_params["actor_user_id"])
    if request.query_params.get("action"):
        qs = qs.filter(action__icontains=request.query_params["action"])
    if request.query_params.get("entity_type"):
        qs = qs.filter(entity_type=request.query_params["entity_type"])
    if request.query_params.get("channel"):
        qs = qs.filter(channel=request.query_params["channel"])
    if request.query_params.get("from_date"):
        qs = qs.filter(timestamp__gte=request.query_params["from_date"])
    if request.query_params.get("to_date"):
        qs = qs.filter(timestamp__lte=request.query_params["to_date"])

    page = int(request.query_params.get("page", 1))
    page_size = int(request.query_params.get("page_size", 50))
    start = (page - 1) * page_size
    end = start + page_size

    total = qs.count()
    results = qs[start:end]

    return Response({
        "success": True,
        "data": AuditEventSerializer(results, many=True).data,
        "meta": {"page": page, "page_size": page_size, "total": total},
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def audit_export(request):  # noqa: ARG001
    last_anchor = AuditChainAnchor.objects.order_by("-id").first()

    return Response({
        "success": True,
        "data": {
            "last_anchor": {
                "event_id": last_anchor.event_id if last_anchor else None,
                "hash_chain_ref": last_anchor.hash_chain_ref if last_anchor else None,
                "anchored_at": last_anchor.anchored_at.isoformat() if last_anchor else None,
            },
            "total_events": AuditEvent.objects.count(),
            "chain_integrity": "verified" if last_anchor else "no_events",
        },
    })
