"""Admin surface over HRMS lifecycle events (IAM-F06).

Ingress lives in the ``lifecycle`` app (SCIM listener + signed webhook); these
endpoints let an IAM admin observe what HRMS pushed, replay transient failures,
and resolve move-conflicts (events that could not be applied cleanly).
"""

import logging

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from audit.emit import emit_event
from console.permissions import IsIAMAdmin
from core.responses import error_response, paginated_response, success_response

logger = logging.getLogger("iam.console.hrms")


def _serialize(items):
    return [{
        "id": str(e.id),
        "event_type": e.event_type,
        "target_email": e.target_email,
        "status": e.status,
        "signature_valid": e.signature_valid,
        "result": e.result,
        "error": e.error,
        "replay_count": e.replay_count,
        "received_at": e.received_at,
        "processed_at": e.processed_at,
        "resolved_at": e.resolved_at,
    } for e in items]


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def hrms_events(request):
    from lifecycle.models import HrmsEvent

    qs = HrmsEvent.objects.all()
    status = request.query_params.get("status")
    event_type = request.query_params.get("event_type")
    email = request.query_params.get("email")
    if status:
        qs = qs.filter(status=status)
    if event_type:
        qs = qs.filter(event_type=event_type)
    if email:
        qs = qs.filter(target_email__icontains=email)
    return paginated_response(request, qs, _serialize)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def hrms_event_replay(request, event_id: str):
    from lifecycle.models import HrmsEvent
    from lifecycle.tasks import handle_hrms_event

    try:
        event = HrmsEvent.objects.get(id=event_id)
    except HrmsEvent.DoesNotExist:
        return error_response(message="not_found", status_code=404)

    HrmsEvent.objects.filter(id=event.id).update(replay_count=event.replay_count + 1)
    handle_hrms_event.delay(event.event_type, event.payload, event_id=str(event.id))

    emit_event(actor_user_id=str(request.user.id), action="hrms.event_replayed",
               entity_type="hrms_event", entity_id=str(event.id), channel="console")
    return success_response(data={"id": str(event.id)}, message="event re-queued")


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def hrms_move_conflicts(request):
    from lifecycle.models import HrmsEvent

    qs = HrmsEvent.objects.filter(status=HrmsEvent.Status.CONFLICT, event_type=HrmsEvent.EventType.MOVER)
    return paginated_response(request, qs, _serialize)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def hrms_move_conflict_resolve(request, event_id: str):
    """Resolve a move-conflict. Body: {"action": "replay"|"dismiss", "note": "..."}."""
    from django.utils import timezone

    from lifecycle.models import HrmsEvent
    from lifecycle.tasks import handle_hrms_event

    try:
        event = HrmsEvent.objects.get(id=event_id)
    except HrmsEvent.DoesNotExist:
        return error_response(message="not_found", status_code=404)
    if event.status != HrmsEvent.Status.CONFLICT:
        return error_response(message="not_in_conflict", status_code=409)

    action = (request.data.get("action") or "dismiss").lower()
    note = request.data.get("note", "")
    if action not in ("replay", "dismiss"):
        return error_response(message="invalid_action", status_code=400)

    event.resolved_by = request.user
    event.resolved_at = timezone.now()
    event.resolution_note = note
    event.status = HrmsEvent.Status.RESOLVED
    event.save(update_fields=["resolved_by", "resolved_at", "resolution_note", "status"])

    if action == "replay":
        handle_hrms_event.delay(event.event_type, event.payload, event_id=str(event.id))

    emit_event(actor_user_id=str(request.user.id), action=f"hrms.conflict_{action}",
               entity_type="hrms_event", entity_id=str(event.id), channel="console",
               metadata={"note": note})
    return success_response(data={"id": str(event.id), "action": action}, message="conflict resolved")
