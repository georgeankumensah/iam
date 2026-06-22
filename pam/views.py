from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import PamSession


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_session(request):
    user = request.user
    target_id = request.data.get("target_id", "")
    target_host = request.data.get("target_host", "")
    vault_lease_id = request.data.get("vault_lease_id", "")

    session = PamSession.objects.create(
        user=user,
        target_id=target_id,
        target_host=target_host,
        vault_lease_id=vault_lease_id,
        started_at=__import__("django").utils.timezone.now(),
    )
    return Response({"id": str(session.id), "status": "active"}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def end_session(request, session_id: str):
    try:
        session = PamSession.objects.get(id=session_id, user=request.user)
        session.status = PamSession.SessionStatus.ENDED
        session.ended_at = __import__("django").utils.timezone.now()
        session.recording_uri = request.data.get("recording_uri", session.recording_uri)
        session.recording_sha256 = request.data.get("recording_sha256", session.recording_sha256)
        session.save()
        return Response({"status": "ended"})
    except PamSession.DoesNotExist:
        return Response({"error": "not_found"}, status=status.HTTP_404_NOT_FOUND)
