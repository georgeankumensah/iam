"""Admin views for Data Residency (N10) and DPIA (N11) compliance."""

from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from audit.emit import emit_event
from console.permissions import IsIAMAdmin
from core.responses import error_response, success_response


def _serialize_residency(items):
    return [{
        "id": str(r.id),
        "service_name": r.service_name,
        "region": r.region,
        "data_classification": r.data_classification,
        "is_backup": r.is_backup,
        "backup_region": r.backup_region,
        "last_reviewed_at": r.last_reviewed_at.isoformat() if r.last_reviewed_at else None,
        "notes": r.notes,
    } for r in items]


def _serialize_dpia(items):
    return [{
        "id": str(d.id),
        "title": d.title,
        "document_ref": d.document_ref,
        "status": d.status,
        "signed_at": d.signed_at.isoformat() if d.signed_at else None,
        "review_date": d.review_date.isoformat() if d.review_date else None,
    } for d in items]


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def residency_list(request):
    from .models import DataResidency

    if request.method == "GET":
        qs = DataResidency.objects.all()
        return success_response(data=_serialize_residency(qs))

    service_name = request.data.get("service_name", "").strip()
    region = request.data.get("region", "ghana")
    if not service_name:
        return error_response(message="service_name is required", status_code=400)

    record, created = DataResidency.objects.update_or_create(
        service_name=service_name,
        defaults={
            "region": region,
            "data_classification": request.data.get("data_classification", "confidential"),
            "is_backup": request.data.get("is_backup", False),
            "backup_region": request.data.get("backup_region", ""),
            "notes": request.data.get("notes", ""),
        },
    )
    emit_event(
        actor_user_id=str(request.user.id), action="compliance.residency_upserted",
        entity_type="data_residency", entity_id=str(record.id), channel="console",
    )
    return success_response(
        data=_serialize_residency([record]), status_code=201 if created else 200,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def residency_review(request, residency_id: str):
    from .models import DataResidency

    try:
        record = DataResidency.objects.get(id=residency_id)
    except DataResidency.DoesNotExist:
        return error_response(message="not_found", status_code=404)

    record.last_reviewed_at = timezone.now()
    record.reviewed_by = request.user
    record.save(update_fields=["last_reviewed_at", "reviewed_by"])

    emit_event(
        actor_user_id=str(request.user.id), action="compliance.residency_reviewed",
        entity_type="data_residency", entity_id=str(record.id), channel="console",
    )
    return success_response(data=_serialize_residency([record]), message="residency reviewed")


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def dpia_list(request):
    from .models import DPIA

    if request.method == "GET":
        qs = DPIA.objects.all()
        return success_response(data=_serialize_dpia(qs))

    title = request.data.get("title", "").strip()
    if not title:
        return error_response(message="title is required", status_code=400)

    review_date_raw = request.data.get("review_date")
    review_date = None
    if review_date_raw:
        from django.utils.dateparse import parse_datetime
        review_date = parse_datetime(review_date_raw)

    record = DPIA.objects.create(
        title=title,
        document_ref=request.data.get("document_ref", ""),
        description=request.data.get("description", ""),
        signed_by=request.user if request.data.get("sign", False) else None,
        signed_at=timezone.now() if request.data.get("sign", False) else None,
        review_date=review_date,
        status="signed" if request.data.get("sign", False) else "draft",
    )
    emit_event(
        actor_user_id=str(request.user.id), action="compliance.dpia_created",
        entity_type="dpia", entity_id=str(record.id), channel="console",
    )
    return success_response(data=_serialize_dpia([record]), status_code=201)
