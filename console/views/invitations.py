import logging

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from accounts.models import Invitation
from clients.models import OIDCClient
from console.onboarding import (
    OnboardingError,
    accept_invitation,
    invite_user,
    resend_invitation,
    revoke_invitation,
)
from console.permissions import can_manage_system_invites, is_iam_admin, is_system_admin
from rbac.models import Role, RoleBinding
from rbac.services import SoDViolation

logger = logging.getLogger("iam.console.invitations")


def _serialize(inv: Invitation) -> dict:
    return {
        "id": str(inv.id),
        "email": inv.email,
        "system_code": inv.system_code,
        "role_ids": inv.role_ids,
        "zitadel_user_id": inv.zitadel_user_id,
        "as_admin": inv.as_admin,
        "status": inv.status,
        "expires_at": inv.expires_at,
        "accepted_at": inv.accepted_at,
        "created_at": inv.created_at,
    }


def manageable_systems(user) -> list[str]:
    """System codes the caller may invite into."""
    codes = list(
        OIDCClient.objects.exclude(system_code="").values_list("system_code", flat=True).distinct()
    )
    if is_iam_admin(user):
        return codes
    return [c for c in codes if is_system_admin(user, c)]


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def invitations_collection(request):
    """List invitations (scoped to systems you manage) or create one.

    POST body: { email, system_code, role_ids[] }
      - IAM admin may invite into any system, any role.
      - A system admin may invite only into systems they administer; granting an
        admin-tier role goes to DG approval before it takes effect.
    """
    if request.method == "GET":
        wanted = request.query_params.get("system_code")
        allowed = manageable_systems(request.user)
        if wanted:
            if wanted not in allowed:
                return Response({"success": False, "error": "forbidden"}, status=status.HTTP_403_FORBIDDEN)
            allowed = [wanted]
        qs = Invitation.objects.filter(system_code__in=allowed).order_by("-created_at")
        return Response({"success": True, "data": [_serialize(i) for i in qs]})

    email = (request.data.get("email") or "").strip().lower()
    system_code = (request.data.get("system_code") or "").strip()
    role_id = request.data.get("role_id")
    first_name = (request.data.get("first_name") or "").strip()
    last_name = (request.data.get("last_name") or "").strip()
    effective_date = request.data.get("effective_date")

    if not email or not system_code or not role_id:
        return Response(
            {"success": False, "error": "email, system_code and role_id are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not can_manage_system_invites(request.user, system_code):
        return Response({"success": False, "error": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

    if not OIDCClient.objects.filter(system_code=system_code).exists():
        return Response({"success": False, "error": "unknown_system"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        role = Role.objects.get(id=role_id, system_code=system_code, is_deprecated=False)
    except Role.DoesNotExist:
        return Response({"success": False, "error": "role_not_found"}, status=status.HTTP_404_NOT_FOUND)

    try:
        inv, code = invite_user(
            email=email,
            system_code=system_code,
            role_ids=[str(role.id)],
            first_name=first_name,
            last_name=last_name,
            invited_by=request.user,
            return_code=bool(request.data.get("return_code", False)),
        )
    except SoDViolation as e:
        return Response(
            {"success": False, "error": "ROLE_CONFLICT", "message": str(e)},
            status=status.HTTP_409_CONFLICT,
        )
    except OnboardingError as e:
        return Response({"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    if effective_date and inv.user:
        binding = RoleBinding.objects.get(user=inv.user, role=role)
        binding.effective_from = effective_date
        binding.save(update_fields=["effective_from"])

    assignment_id = None
    if inv.user:
        binding = RoleBinding.objects.filter(user=inv.user, role=role).first()
        assignment_id = str(binding.id) if binding else None

    data = {
        "email": email,
        "system_code": system_code,
        "role_id": str(role.id),
        "assignment_id": assignment_id,
        "effective_date": effective_date or None,
        "client_role_written": True,
        "client_role_error": None,
    }
    return Response({"success": True, "message": "Invite sent.", "data": data}, status=status.HTTP_201_CREATED)


def _load_managed(request, invite_id):
    try:
        inv = Invitation.objects.get(id=invite_id)
    except Invitation.DoesNotExist:
        return None, Response({"success": False, "error": "not_found"}, status=status.HTTP_404_NOT_FOUND)
    if not can_manage_system_invites(request.user, inv.system_code):
        return None, Response({"success": False, "error": "forbidden"}, status=status.HTTP_403_FORBIDDEN)
    return inv, None


@api_view(["GET", "DELETE"])
@permission_classes([IsAuthenticated])
def invitation_detail(request, invite_id: str):
    inv, err = _load_managed(request, invite_id)
    if err:
        return err
    if request.method == "GET":
        return Response({"success": True, "data": _serialize(inv)})
    revoke_invitation(inv, actor=request.user)
    return Response({"success": True, "data": _serialize(inv)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def invitation_resend(request, invite_id: str):
    inv, err = _load_managed(request, invite_id)
    if err:
        return err
    code = resend_invitation(inv, return_code=bool(request.data.get("return_code", False)))
    data = _serialize(inv)
    if code:
        data["invite_code"] = code
    return Response({"success": True, "data": data})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_admin_systems(request):
    """Systems the caller can invite into, with each system's assignable roles.

    Lets a system-admin UI show only their systems and only roles they may grant.
    """
    out = []
    for code in manageable_systems(request.user):
        client = OIDCClient.objects.filter(system_code=code).first()
        roles = Role.objects.filter(system_code=code, is_deprecated=False).order_by("role_id")
        out.append({
            "system_code": code,
            "name": client.name if client else code,
            "roles": [
                {"id": str(r.id), "role_id": r.role_id, "name": r.name, "is_admin": r.is_admin}
                for r in roles
            ],
        })
    return Response({"success": True, "data": out})


def _internal_actor(request):
    if request.headers.get("X-Internal-Secret") != settings.ONBOARDING_INTERNAL_SECRET:
        return None, Response({"success": False, "error": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

    from accounts.models import User

    uid = request.data.get("actor_zitadel_user_id") or request.query_params.get("actor_zitadel_user_id")
    if not uid:
        return None, Response({"success": False, "error": "missing actor"}, status=status.HTTP_400_BAD_REQUEST)

    actor = User.objects.filter(zitadel_user_id=uid, status="active").first()
    if not actor:
        return None, Response({"success": False, "error": "actor_not_found"}, status=status.HTTP_403_FORBIDDEN)
    return actor, None


@api_view(["GET"])
@permission_classes([AllowAny])
def internal_admin_systems(request):
    """Internal bridge for the login-app admin console."""
    actor, err = _internal_actor(request)
    if err:
        return err

    out = []
    for code in manageable_systems(actor):
        client = OIDCClient.objects.filter(system_code=code).first()
        roles = Role.objects.filter(system_code=code, is_deprecated=False).order_by("role_id")
        out.append({
            "system_code": code,
            "name": client.name if client else code,
            "roles": [
                {"id": str(r.id), "role_id": r.role_id, "name": r.name, "is_admin": r.is_admin}
                for r in roles
            ],
        })
    return Response({"success": True, "data": out})


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def internal_invitations(request):
    """Internal bridge for login-app invite creation/listing.

    The browser never receives the internal secret. The login-app server passes
    the authenticated ZITADEL user id from its session cookie; IAM still checks
    whether that user can manage the requested system.
    """
    actor, err = _internal_actor(request)
    if err:
        return err

    if request.method == "GET":
        allowed = manageable_systems(actor)
        qs = Invitation.objects.filter(system_code__in=allowed).order_by("-created_at")[:25]
        return Response({"success": True, "data": [_serialize(i) for i in qs]})

    email = (request.data.get("email") or "").strip().lower()
    system_code = (request.data.get("system_code") or "").strip()
    role_ids = request.data.get("role_ids") or []

    if not email or not system_code:
        return Response(
            {"success": False, "error": "email and system_code are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not can_manage_system_invites(actor, system_code):
        return Response({"success": False, "error": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

    try:
        inv, code = invite_user(
            email=email,
            system_code=system_code,
            role_ids=role_ids,
            invited_by=actor,
            return_code=bool(request.data.get("return_code", True)),
        )
    except SoDViolation as e:
        return Response(
            {"success": False, "error": "ROLE_CONFLICT", "message": str(e)},
            status=status.HTTP_409_CONFLICT,
        )
    except OnboardingError as e:
        return Response({"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    data = _serialize(inv)
    if code:
        data["invite_code"] = code
    return Response({"success": True, "data": data}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
def internal_invitation_resend(request, invite_id: str):
    """Internal bridge for login-app invite resend."""
    actor, err = _internal_actor(request)
    if err:
        return err

    try:
        inv = Invitation.objects.get(id=invite_id)
    except Invitation.DoesNotExist:
        return Response({"success": False, "error": "not_found"}, status=status.HTTP_404_NOT_FOUND)

    if not can_manage_system_invites(actor, inv.system_code):
        return Response({"success": False, "error": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

    code = resend_invitation(inv, return_code=True)
    inv.refresh_from_db()
    data = _serialize(inv)
    if code:
        data["invite_code"] = code
    return Response({"success": True, "data": data})


@api_view(["POST"])
@permission_classes([AllowAny])
def invitation_accept(request):
    """Internal endpoint called by the login-app when an invitee sets a password."""
    if request.headers.get("X-Internal-Secret") != settings.ONBOARDING_INTERNAL_SECRET:
        return Response({"success": False, "error": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

    uid = request.data.get("zitadel_user_id")
    code = request.data.get("code")
    password = request.data.get("password")
    if not (uid and code and password):
        return Response({"success": False, "error": "missing fields"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        result = accept_invitation(zitadel_user_id=uid, code=code, password=password)
    except Exception as e:  # noqa: BLE001
        logger.warning("invitation accept failed: %s", e)
        return Response({"success": False, "error": "invalid_or_expired"}, status=status.HTTP_400_BAD_REQUEST)

    return Response({"success": True, "data": result})
