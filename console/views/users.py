import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import User
from audit.emit import emit_event
from console.permissions import IsIAMAdmin
from console.selectors import list_users
from console.serializers import BulkImportSerializer, UserCreateSerializer, UserUpdateSerializer
from console.services import create_user_in_zitadel, deactivate_user_in_zitadel

logger = logging.getLogger("iam.console.users")


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def users_list(request):
    if request.method == "GET":
        user_type = request.query_params.get("user_type")
        status = request.query_params.get("status")
        search = request.query_params.get("search")

        qs = list_users(user_type=user_type, status=status, search=search)

        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 50))
        start = (page - 1) * page_size
        end = start + page_size

        total = qs.count()
        results = qs[start:end]

        from accounts.serializers import UserSerializer
        serializer = UserSerializer(results, many=True)

        return Response({
            "success": True,
            "data": serializer.data,
            "meta": {"page": page, "page_size": page_size, "total": total},
        })

    elif request.method == "POST":
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        zitadel_result = create_user_in_zitadel(serializer.validated_data["email"])
        user = serializer.save()

        if zitadel_result and zitadel_result.get("userId"):
            user.zitadel_user_id = zitadel_result["userId"]
            user.save(update_fields=["zitadel_user_id"])

        emit_event(
            actor_user_id=str(request.user.id),
            action="user.created",
            entity_type="user",
            entity_id=str(user.id),
            channel="console",
        )

        return Response({"success": True, "data": {"id": str(user.id)}}, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def users_detail(request, user_id: str):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"error": "not_found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        from accounts.serializers import UserSerializer
        return Response({"success": True, "data": UserSerializer(user).data})

    elif request.method == "PATCH":
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        emit_event(
            actor_user_id=str(request.user.id),
            action="user.updated",
            entity_type="user",
            entity_id=str(user.id),
            channel="console",
        )

        return Response({"success": True, "data": {"id": str(user.id)}})

    elif request.method == "DELETE":
        if user.zitadel_user_id:
            deactivate_user_in_zitadel(str(user.zitadel_user_id))
        user.status = User.UserStatus.DISABLED
        user.save(update_fields=["status"])

        emit_event(
            actor_user_id=str(request.user.id),
            action="user.deactivated",
            entity_type="user",
            entity_id=str(user.id),
            channel="console",
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def user_roles(request, user_id: str):
    """All of a user's role bindings across systems."""
    from core.responses import error_response, success_response
    from rbac.models import RoleBinding

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return error_response(message="not_found", status_code=404)

    bindings = RoleBinding.objects.filter(user=user).select_related("role").order_by("role__system_code", "role__role_id")
    data = [{
        "binding_id": str(b.id),
        "system_code": b.role.system_code,
        "role_id": b.role.role_id,
        "is_admin": b.role.is_admin,
        "state": b.state,
        "effective_from": b.effective_from,
        "effective_to": b.effective_to,
    } for b in bindings]
    return success_response(data=data)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def users_bulk_import(request):
    serializer = BulkImportSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    from console.onboarding import invite_user
    from rbac.models import Role

    results: list[dict] = []
    for user_data in serializer.validated_data["users"]:
        email = user_data.get("email", "")
        system_code = (user_data.get("system_code") or "").strip()
        role_code = (user_data.get("role") or "").strip()
        try:
            if system_code:
                # Onboard into a system: creates the user, grants the role, and
                # emails an invite — the same path as a single invitation.
                role_ids = []
                if role_code:
                    role = Role.objects.filter(system_code=system_code, role_id=role_code).first()
                    if role:
                        role_ids = [str(role.id)]
                inv, _ = invite_user(
                    email=email, system_code=system_code, role_ids=role_ids,
                    invited_by=request.user, return_code=False,
                )
                results.append({"email": email, "status": "invited", "id": str(inv.id)})
            else:
                zitadel_result = create_user_in_zitadel(email)
                user = User.objects.create(
                    email=email,
                    user_type=user_data.get("user_type", "external"),
                    metadata=user_data.get("metadata", {}),
                )
                if zitadel_result and zitadel_result.get("userId"):
                    user.zitadel_user_id = zitadel_result["userId"]
                    user.save(update_fields=["zitadel_user_id"])
                results.append({"email": email, "status": "created", "id": str(user.id)})
        except Exception as e:
            results.append({"email": email, "status": "error", "error": str(e)})

    emit_event(
        actor_user_id=str(request.user.id),
        action="user.bulk_import",
        entity_type="user",
        channel="console",
        metadata={"total": len(results), "success": sum(1 for r in results if r["status"] == "created")},
    )

    return Response({"success": True, "data": {"results": results}})
