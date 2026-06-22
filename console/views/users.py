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


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def users_bulk_import(request):
    serializer = BulkImportSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    results: list[dict] = []
    for user_data in serializer.validated_data["users"]:
        try:
            zitadel_result = create_user_in_zitadel(user_data["email"])
            user = User.objects.create(**user_data)
            if zitadel_result and zitadel_result.get("userId"):
                user.zitadel_user_id = zitadel_result["userId"]
                user.save(update_fields=["zitadel_user_id"])
            results.append({"email": user_data["email"], "status": "created", "id": str(user.id)})
        except Exception as e:
            results.append({"email": user_data["email"], "status": "error", "error": str(e)})

    emit_event(
        actor_user_id=str(request.user.id),
        action="user.bulk_import",
        entity_type="user",
        channel="console",
        metadata={"total": len(results), "success": sum(1 for r in results if r["status"] == "created")},
    )

    return Response({"success": True, "data": {"results": results}})
