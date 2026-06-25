from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from audit.emit import emit_event
from clients.models import ClientLifecycleState, OIDCClient
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
        # Provision a brand-new system: ZITADEL project + SPA app + roles +
        # Django mirror. Body: { system_code, name, frontend_port? |
        # redirect_uris?, roles: [{role_id, name, is_admin?}] }.
        from clients.services import provision_system, redirect_uris_for_port

        code = (request.data.get("system_code") or "").strip()
        name = (request.data.get("name") or code).strip()
        if not code:
            return Response({"success": False, "error": "system_code required"}, status=status.HTTP_400_BAD_REQUEST)

        port = request.data.get("frontend_port")
        if port:
            redirects, logout = redirect_uris_for_port(int(port))
        else:
            redirects = request.data.get("redirect_uris") or []
            logout = request.data.get("post_logout_redirect_uris") or []
        if not redirects:
            return Response(
                {"success": False, "error": "frontend_port or redirect_uris required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        roles = [
            (r["role_id"], r.get("name", r["role_id"]), bool(r.get("is_admin", False)))
            for r in (request.data.get("roles") or [])
            if r.get("role_id")
        ]

        try:
            res = provision_system(
                code=code, project_name=name,
                redirect_uris=redirects, post_logout_uris=logout, roles=roles,
            )
        except Exception as e:  # noqa: BLE001
            return Response({"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        emit_event(
            actor_user_id=str(request.user.id),
            action="client.created",
            entity_type="oidc_client",
            entity_id=res["client_id"],
            channel="console",
            metadata={"system_code": code, "project_id": res["project_id"]},
        )

        return Response({"success": True, "data": res}, status=status.HTTP_201_CREATED)


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

    client.lifecycle_state = ClientLifecycleState.PRODUCTION_LIVE
    client.save(update_fields=["lifecycle_state"])

    emit_event(
        actor_user_id=str(request.user.id),
        action="client.promoted",
        entity_type="oidc_client",
        entity_id=client_id,
        channel="console",
    )

    return Response({"success": True, "data": {"id": client_id, "state": "production_live"}})


def _get_client(client_id):
    try:
        return OIDCClient.objects.get(id=client_id), None
    except OIDCClient.DoesNotExist:
        from core.responses import error_response
        return None, error_response(message="not_found", status_code=404)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def client_suspend(request, client_id: str):
    """Suspend a system: deactivate its ZITADEL app and mark it suspended."""
    from core.responses import error_response, success_response
    from core.zitadel import zitadel

    client, err = _get_client(client_id)
    if err:
        return err
    if client.zitadel_project_id and client.zitadel_app_id:
        try:
            zitadel().deactivate_app(client.zitadel_project_id, client.zitadel_app_id)
        except Exception as e:  # noqa: BLE001
            return error_response(message=f"zitadel error: {e}", status_code=400)
    client.lifecycle_state = ClientLifecycleState.SUSPENDED
    client.save(update_fields=["lifecycle_state"])
    emit_event(actor_user_id=str(request.user.id), action="client.suspended",
               entity_type="oidc_client", entity_id=str(client.id), channel="console")
    return success_response(data={"id": str(client.id), "state": client.lifecycle_state})


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def client_activate(request, client_id: str):
    """Reactivate a suspended system."""
    from core.responses import error_response, success_response
    from core.zitadel import zitadel

    client, err = _get_client(client_id)
    if err:
        return err
    if client.zitadel_project_id and client.zitadel_app_id:
        try:
            zitadel().reactivate_app(client.zitadel_project_id, client.zitadel_app_id)
        except Exception as e:  # noqa: BLE001
            return error_response(message=f"zitadel error: {e}", status_code=400)
    client.lifecycle_state = ClientLifecycleState.PRODUCTION_LIVE
    client.save(update_fields=["lifecycle_state"])
    emit_event(actor_user_id=str(request.user.id), action="client.activated",
               entity_type="oidc_client", entity_id=str(client.id), channel="console")
    return success_response(data={"id": str(client.id), "state": client.lifecycle_state})


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def client_rotate_secret(request, client_id: str):
    """Rotate a confidential client's secret (returns it once)."""
    from django.utils import timezone

    from core.responses import error_response, success_response
    from core.zitadel import zitadel

    client, err = _get_client(client_id)
    if err:
        return err
    if not (client.zitadel_project_id and client.zitadel_app_id):
        return error_response(message="client has no zitadel app", status_code=400)
    try:
        result = zitadel().regenerate_app_secret(client.zitadel_project_id, client.zitadel_app_id)
    except Exception as e:  # noqa: BLE001
        return error_response(message=f"zitadel error: {e}", status_code=400)
    client.secret_rotated_at = timezone.now()
    client.save(update_fields=["secret_rotated_at"])
    emit_event(actor_user_id=str(request.user.id), action="client.secret_rotated",
               entity_type="oidc_client", entity_id=str(client.id), channel="console")
    return success_response(data={"client_secret": result.get("clientSecret", "")},
                            message="store this secret now; it will not be shown again")
