from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from audit.emit import emit_event
from console.permissions import IsIAMAdmin
from rbac.models import Role, RoleBinding


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
        serializer.save()

        emit_event(
            actor_user_id=str(request.user.id),
            action="role.created",
            entity_type="role",
            entity_id=serializer.data.get("id", ""),
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

    emit_event(
        actor_user_id=str(request.user.id),
        action="role.bound",
        entity_type="role_binding",
        entity_id=str(binding.id),
        channel="console",
    )

    return Response({"success": True, "data": {"id": str(binding.id)}}, status=status.HTTP_201_CREATED)
