import logging

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from accounts.models import Invitation
from console.onboarding import (
    OnboardingError,
    accept_invitation,
    invite_user,
    resend_invitation,
    revoke_invitation,
)
from console.permissions import can_manage_system_invites
from rbac.services import SoDViolation

logger = logging.getLogger("iam.console.invitations")


def _serialize(inv: Invitation) -> dict:
    return {
        "id": str(inv.id),
        "email": inv.email,
        "system_code": inv.system_code,
        "role_ids": inv.role_ids,
        "as_admin": inv.as_admin,
        "status": inv.status,
        "expires_at": inv.expires_at,
        "accepted_at": inv.accepted_at,
        "created_at": inv.created_at,
    }


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def invitations_list(request, system_code: str):
    if not can_manage_system_invites(request.user, system_code):
        return Response({"success": False, "error": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

    if request.method == "GET":
        qs = Invitation.objects.filter(system_code=system_code).order_by("-created_at")
        return Response({"success": True, "data": [_serialize(i) for i in qs]})

    email = (request.data.get("email") or "").strip().lower()
    if not email:
        return Response({"success": False, "error": "email required"}, status=status.HTTP_400_BAD_REQUEST)
    role_ids = request.data.get("role_ids") or []
    return_code = bool(request.data.get("return_code", False))

    try:
        inv, code = invite_user(
            email=email,
            system_code=system_code,
            role_ids=role_ids,
            invited_by=request.user,
            return_code=return_code,
        )
    except SoDViolation as e:
        return Response(
            {"success": False, "error": "ROLE_CONFLICT", "message": str(e)},
            status=status.HTTP_409_CONFLICT,
        )
    except OnboardingError as e:
        return Response({"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    data = _serialize(inv)
    if code:  # dev/return_code mode
        data["invite_code"] = code
    return Response({"success": True, "data": data}, status=status.HTTP_201_CREATED)


@api_view(["GET", "DELETE"])
@permission_classes([IsAuthenticated])
def invitation_detail(request, system_code: str, invite_id: str):
    if not can_manage_system_invites(request.user, system_code):
        return Response({"success": False, "error": "forbidden"}, status=status.HTTP_403_FORBIDDEN)
    try:
        inv = Invitation.objects.get(id=invite_id, system_code=system_code)
    except Invitation.DoesNotExist:
        return Response({"success": False, "error": "not_found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response({"success": True, "data": _serialize(inv)})

    revoke_invitation(inv, actor=request.user)
    return Response({"success": True, "data": _serialize(inv)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def invitation_resend(request, system_code: str, invite_id: str):
    if not can_manage_system_invites(request.user, system_code):
        return Response({"success": False, "error": "forbidden"}, status=status.HTTP_403_FORBIDDEN)
    try:
        inv = Invitation.objects.get(id=invite_id, system_code=system_code)
    except Invitation.DoesNotExist:
        return Response({"success": False, "error": "not_found"}, status=status.HTTP_404_NOT_FOUND)

    code = resend_invitation(inv, return_code=bool(request.data.get("return_code", False)))
    data = _serialize(inv)
    if code:
        data["invite_code"] = code
    return Response({"success": True, "data": data})


@api_view(["POST"])
@permission_classes([AllowAny])
def invitation_accept(request):
    """Internal endpoint called by the login-app when an invitee sets a password.

    Authenticated by a shared secret (server-to-server only); the ZITADEL invite
    code is itself the user's proof.
    """
    if request.headers.get("X-Internal-Secret") != settings.ONBOARDING_INTERNAL_SECRET:
        return Response({"success": False, "error": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

    uid = request.data.get("zitadel_user_id")
    code = request.data.get("code")
    password = request.data.get("password")
    if not (uid and code and password):
        return Response({"success": False, "error": "missing fields"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        result = accept_invitation(zitadel_user_id=uid, code=code, password=password)
    except Exception as e:  # noqa: BLE001 - surface ZITADEL errors as 400
        logger.warning("invitation accept failed: %s", e)
        return Response({"success": False, "error": "invalid_or_expired"}, status=status.HTTP_400_BAD_REQUEST)

    return Response({"success": True, "data": result})
