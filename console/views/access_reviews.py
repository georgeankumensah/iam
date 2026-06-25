"""Quarterly access-review campaigns (IAM-F03-03)."""

import logging

from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from audit.emit import emit_event
from console.permissions import IsIAMAdmin
from core.responses import error_response, paginated_response, success_response
from rbac.models import AccessReviewCampaign, AccessReviewItem
from rbac.review_services import apply_decision, decision_counts, generate_items, sign_report

logger = logging.getLogger("iam.console.access_reviews")


def _serialize_campaign(c) -> dict:
    return {
        "id": str(c.id), "name": c.name, "period": c.period, "scope": c.scope,
        "status": c.status, "completed_at": c.completed_at,
        "signed_report_ref": c.signed_report_ref, "created_at": c.created_at,
        "counts": decision_counts(c),
    }


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def campaigns(request):
    if request.method == "GET":
        qs = AccessReviewCampaign.objects.all().order_by("-created_at")
        return paginated_response(request, qs, lambda items: [_serialize_campaign(c) for c in items])

    name = (request.data.get("name") or "").strip()
    period = (request.data.get("period") or "").strip()
    scope = request.data.get("scope") or {}
    if not name or not period:
        return error_response(message="name and period are required", status_code=400)

    campaign = AccessReviewCampaign.objects.create(
        name=name, period=period, scope=scope, created_by=request.user,
    )
    count = generate_items(campaign)
    emit_event(actor_user_id=str(request.user.id), action="access_review.created",
               entity_type="access_review", entity_id=str(campaign.id), channel="console",
               metadata={"period": period, "items": count})
    data = _serialize_campaign(campaign)
    data["items_generated"] = count
    return success_response(data=data, status_code=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def campaign_detail(request, campaign_id: str):
    try:
        c = AccessReviewCampaign.objects.get(id=campaign_id)
    except AccessReviewCampaign.DoesNotExist:
        return error_response(message="not_found", status_code=404)
    return success_response(data=_serialize_campaign(c))


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def campaign_items(request, campaign_id: str):
    try:
        c = AccessReviewCampaign.objects.get(id=campaign_id)
    except AccessReviewCampaign.DoesNotExist:
        return error_response(message="not_found", status_code=404)
    qs = c.items.select_related("user", "new_role").order_by("system_code", "user__email")
    decision = request.query_params.get("decision")
    if decision:
        qs = qs.filter(decision=decision)

    def serialize(items):
        return [{
            "id": str(i.id),
            "user": {"id": str(i.user.id), "email": i.user.email},
            "system_code": i.system_code, "role_id": i.role_id,
            "decision": i.decision,
            "new_role": i.new_role.role_id if i.new_role else None,
            "reviewer": i.reviewer.email if i.reviewer else None,
            "decided_at": i.decided_at, "note": i.note,
        } for i in items]

    return paginated_response(request, qs, serialize)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def item_decide(request, item_id: str):
    try:
        item = AccessReviewItem.objects.select_related("campaign", "user", "binding__role").get(id=item_id)
    except AccessReviewItem.DoesNotExist:
        return error_response(message="not_found", status_code=404)
    if item.campaign.status != AccessReviewCampaign.Status.OPEN:
        return error_response(message="campaign_closed", status_code=409)

    decision = request.data.get("decision")
    if decision not in AccessReviewItem.Decision.values:
        return error_response(message="invalid decision", status_code=400)

    try:
        apply_decision(
            item, decision, reviewer=request.user,
            new_role_id=request.data.get("new_role_id", ""),
            note=request.data.get("note", ""),
        )
    except ValueError as e:
        return error_response(message=str(e), status_code=400)

    emit_event(actor_user_id=str(request.user.id), action="access_review.decided",
               entity_type="access_review_item", entity_id=str(item.id), channel="console",
               metadata={"decision": decision})
    return success_response(data={"id": str(item.id), "decision": decision})


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def campaign_complete(request, campaign_id: str):
    """Close the campaign once every item is decided; sign the report."""
    try:
        c = AccessReviewCampaign.objects.get(id=campaign_id)
    except AccessReviewCampaign.DoesNotExist:
        return error_response(message="not_found", status_code=404)
    if c.status == AccessReviewCampaign.Status.COMPLETED:
        return error_response(message="already_completed", status_code=409)
    if c.items.filter(decision=AccessReviewItem.Decision.PENDING).exists():
        return error_response(message="undecided_items_remain", status_code=409)

    report = sign_report(c, request.user)
    c.status = AccessReviewCampaign.Status.COMPLETED
    c.completed_at = timezone.now()
    c.completed_by = request.user
    c.signed_report_ref = report["digest"]
    c.save(update_fields=["status", "completed_at", "completed_by", "signed_report_ref", "updated_at"])

    emit_event(actor_user_id=str(request.user.id), action="access_review.completed",
               entity_type="access_review", entity_id=str(c.id), channel="console",
               metadata={"digest": report["digest"]})
    return success_response(data={"id": str(c.id), "digest": report["digest"]}, message="campaign completed")


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def campaign_export(request, campaign_id: str):
    """Return the signed decision report (recomputed deterministically)."""
    try:
        c = AccessReviewCampaign.objects.get(id=campaign_id)
    except AccessReviewCampaign.DoesNotExist:
        return error_response(message="not_found", status_code=404)
    report = sign_report(c, c.completed_by or request.user)
    return success_response(data=report)
