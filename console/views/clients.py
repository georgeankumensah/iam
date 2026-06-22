from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from audit.emit import emit_event
from clients.models import OIDCClient
from console.permissions import IsIAMAdmin


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def clients_list(request):
    if request.method == "GET":
        lifecycle_state = request.query_params.get("lifecycle_state")
        qs = OIDCClient.objects.all()
        if lifecycle_state:
            qs = qs.filter(lifecycle_state=lifecycle_state)
        qs = qs.order_by("-created_at")

        from clients.serializers import OIDCClientSerializer
        return Response({"success": True, "data": OIDCClientSerializer(qs, many=True).data})

    elif request.method == "POST":
        from clients.serializers import OIDCClientCreateSerializer
        serializer = OIDCClientCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client = serializer.save()

        emit_event(
            actor_user_id=str(request.user.id),
            action="client.created",
            entity_type="oidc_client",
            entity_id=str(client.id),
            channel="console",
        )

        return Response({"success": True, "data": {"id": str(client.id)}}, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def client_detail(request, client_id: str):  # noqa: ARG001
    try:
        client = OIDCClient.objects.get(id=client_id)
    except OIDCClient.DoesNotExist:
        return Response({"error": "not_found"}, status=status.HTTP_404_NOT_FOUND)

    from clients.serializers import OIDCClientSerializer
    return Response({"success": True, "data": OIDCClientSerializer(client).data})


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def client_promote(request, client_id: str):
    try:
        client = OIDCClient.objects.get(id=client_id)
    except OIDCClient.DoesNotExist:
        return Response({"error": "not_found"}, status=status.HTTP_404_NOT_FOUND)

    if not client.compliance_gate_passed:
        return Response({"error": "compliance_gate_not_passed"}, status=status.HTTP_400_BAD_REQUEST)

    client.lifecycle_state = OIDCClient.ClientLifecycleState.PRODUCTION_LIVE
    client.save(update_fields=["lifecycle_state"])

    emit_event(
        actor_user_id=str(request.user.id),
        action="client.promoted",
        entity_type="oidc_client",
        entity_id=client_id,
        channel="console",
    )

    return Response({"success": True, "data": {"id": client_id, "state": "production_live"}})
