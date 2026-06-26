from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.exceptions import NotFoundError, StepUpRequiredError

from .models import PamSession
from .services import broker_pam_session, list_pam_sessions, revoke_pam_session


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def session_list(request):
    if request.method == "GET":
        qs = list_pam_sessions()
        data = [
            {
                "id": str(s.id),
                "user_id": str(s.user.id),
                "user_email": s.user.email,
                "target_id": s.target_id,
                "target_host": s.target_host,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                "status": s.status,
                "recording_uri": s.recording_uri,
                "recording_sha256": s.recording_sha256,
                "vault_lease_id": s.vault_lease_id,
            }
            for s in qs
        ]
        return Response({"data": data})

    user = request.user
    target_id = request.data.get("target_id", "")
    target_host = request.data.get("target_host", "")
    ttl_hours = int(request.data.get("ttl_hours", 1))

    if not target_id:
        return Response({"error": "target_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    session = broker_pam_session(user=user, target_id=target_id, target_host=target_host, ttl_hours=ttl_hours)
    return Response(
        {"id": str(session.id), "status": session.status, "vault_lease_id": session.vault_lease_id},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def end_session(request, session_id: str):
    try:
        session = PamSession.objects.get(id=session_id, user=request.user)
    except PamSession.DoesNotExist as e:
        raise NotFoundError("PAM session not found") from e

    session.status = PamSession.SessionStatus.ENDED
    session.ended_at = __import__("django").utils.timezone.now()
    session.recording_uri = request.data.get("recording_uri", session.recording_uri)
    session.recording_sha256 = request.data.get("recording_sha256", session.recording_sha256)
    session.save()
    return Response({"status": "ended"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def revoke_session(request, session_id: str):
    has_step_up = request.auth and getattr(request.auth, "mfa_verified", False) if hasattr(request, "auth") else False
    if not has_step_up:
        raise StepUpRequiredError("Step-up MFA (vault:operate) required to revoke PAM sessions")

    try:
        session = PamSession.objects.get(id=session_id)
    except PamSession.DoesNotExist as e:
        raise NotFoundError("PAM session not found") from e

    reason = request.data.get("reason", "admin_revoke")
    with transaction.atomic():
        revoke_pam_session(session=session, actor_id=str(request.user.id), reason=reason)
    return Response({"status": "revoked", "id": str(session.id)})
