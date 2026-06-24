import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from audit.emit import emit_event
from console.permissions import IsDG, IsIAMAdmin
from rbac.models import Role, RoleBinding

logger = logging.getLogger("iam.console.roles")


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def roles_list(request):
    if request.method == "GET":
        system_code = request.query_params.get("system_code")
        qs = Role.objects.all()
        if system_code:
            qs = qs.filter(system_code=system_code)
        qs = qs.order_by("system_code", "role_id")

        from rbac.serializers import RoleSerializer
        return Response({"success": True, "data": RoleSerializer(qs, many=True).data})

    elif request.method == "POST":
        from rbac.serializers import RoleSerializer
        serializer = RoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = serializer.save()

        # Keep ZITADEL in sync: create the project role so it can be granted and
        # appear in tokens. Best-effort — a role for a system with no provisioned
        # project is still recorded locally.
        from clients.models import OIDCClient
        client = OIDCClient.objects.filter(system_code=role.system_code).exclude(zitadel_project_id="").first()
        if client:
            try:
                from core.zitadel import zitadel
                zitadel().ensure_project_role(client.zitadel_project_id, role.role_id, role.name, group=role.system_code)
            except Exception:  # noqa: BLE001
                logger.warning("could not push role %s to ZITADEL", role.role_id)

        emit_event(
            actor_user_id=str(request.user.id),
            action="role.created",
            entity_type="role",
            entity_id=str(role.id),
            channel="console",
        )

        return Response({"success": True, "data": serializer.data}, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def role_detail(request, role_id: str):
    try:
        role = Role.objects.get(id=role_id)
    except Role.DoesNotExist:
        return Response({"error": "not_found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        from rbac.serializers import RoleSerializer
        return Response({"success": True, "data": RoleSerializer(role).data})

    elif request.method == "PATCH":
        from rbac.serializers import RoleSerializer
        serializer = RoleSerializer(role, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        emit_event(
            actor_user_id=str(request.user.id),
            action="role.updated",
            entity_type="role",
            entity_id=role_id,
            channel="console",
        )

        return Response({"success": True, "data": serializer.data})


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def role_bind(request, role_id: str):
    try:
        role = Role.objects.get(id=role_id)
    except Role.DoesNotExist:
        return Response({"error": "not_found"}, status=status.HTTP_404_NOT_FOUND)

    user_id = request.data.get("user_id")
    justification = request.data.get("justification", "")

    try:
        from accounts.models import User
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"error": "user_not_found"}, status=status.HTTP_404_NOT_FOUND)

    binding = RoleBinding.objects.create(
        role=role,
        user=user,
        state=RoleBinding.BindingState.APPROVED,
        effective_from=request.data.get("effective_from"),
        effective_to=request.data.get("effective_to"),
        justification=justification,
        approver=request.user,
    )

    # Dual-write: push the role into ZITADEL so it appears in the user's tokens.
    from rbac.services import sync_user_system_grant
    sync_user_system_grant(user, role.system_code)

    emit_event(
        actor_user_id=str(request.user.id),
        action="role.bound",
        entity_type="role_binding",
        entity_id=str(binding.id),
        channel="console",
    )

    return Response({"success": True, "data": {"id": str(binding.id)}}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def role_unbind(request, role_id: str):
    try:
        role = Role.objects.get(id=role_id)
    except Role.DoesNotExist:
        return Response({"error": "not_found"}, status=status.HTTP_404_NOT_FOUND)

    user_id = request.data.get("user_id")
    binding = RoleBinding.objects.filter(
        role=role, user_id=user_id, state=RoleBinding.BindingState.APPROVED
    ).first()
    if not binding:
        return Response({"error": "binding_not_found"}, status=status.HTTP_404_NOT_FOUND)

    binding.state = RoleBinding.BindingState.REVOKED
    binding.save(update_fields=["state", "updated_at"])

    from rbac.services import sync_user_system_grant
    sync_user_system_grant(binding.user, role.system_code, reevaluate_sessions=True)

    emit_event(
        actor_user_id=str(request.user.id),
        action="role.unbound",
        entity_type="role_binding",
        entity_id=str(binding.id),
        channel="console",
    )

    return Response({"success": True, "data": {"id": str(binding.id)}})


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsDG])
def bindings_queue(request):
    """DG queue of role bindings awaiting approval (default state=requested)."""
    from core.responses import paginated_response

    state = request.query_params.get("state", RoleBinding.BindingState.REQUESTED)
    qs = RoleBinding.objects.filter(state=state).select_related("role", "user").order_by("created_at")

    def serialize(items):
        return [{
            "id": str(b.id),
            "user": {"id": str(b.user.id), "email": b.user.email},
            "system_code": b.role.system_code,
            "role_id": b.role.role_id,
            "is_admin": b.role.is_admin,
            "justification": b.justification,
            "created_at": b.created_at,
        } for b in items]

    return paginated_response(request, qs, serialize)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsDG])
def binding_reject(request, binding_id: str):
    """DG rejects a requested binding (no grant is pushed)."""
    from core.responses import error_response, success_response

    try:
        binding = RoleBinding.objects.get(id=binding_id)
    except RoleBinding.DoesNotExist:
        return error_response(message="not_found", status_code=404)
    if binding.state != RoleBinding.BindingState.REQUESTED:
        return error_response(message="not_pending", status_code=409)

    binding.state = RoleBinding.BindingState.REVOKED
    binding.approver = request.user
    binding.save(update_fields=["state", "approver", "updated_at"])
    emit_event(actor_user_id=str(request.user.id), action="role.binding_rejected",
               entity_type="role_binding", entity_id=str(binding.id), channel="console")
    return success_response(data={"id": str(binding.id)}, message="rejected")


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsDG])
def binding_approve(request, binding_id: str):
    """DG approval for an elevated/admin binding requested during onboarding.

    Flips a REQUESTED binding to APPROVED and pushes the grant to ZITADEL.
    """
    try:
        binding = RoleBinding.objects.select_related("role").get(id=binding_id)
    except RoleBinding.DoesNotExist:
        return Response({"error": "not_found"}, status=status.HTTP_404_NOT_FOUND)

    if binding.state != RoleBinding.BindingState.REQUESTED:
        return Response({"error": "not_pending"}, status=status.HTTP_409_CONFLICT)

    binding.state = RoleBinding.BindingState.APPROVED
    binding.approver = request.user
    binding.save(update_fields=["state", "approver", "updated_at"])

    from rbac.services import sync_user_system_grant
    sync_user_system_grant(binding.user, binding.role.system_code)

    emit_event(
        actor_user_id=str(request.user.id),
        action="role.binding_approved",
        entity_type="role_binding",
        entity_id=str(binding.id),
        channel="console",
    )

    return Response({"success": True, "data": {"id": str(binding.id)}})
