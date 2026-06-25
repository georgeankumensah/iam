"""Admin endpoints for managing systems (OIDC clients) and their role catalogues."""

import logging

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from audit.emit import emit_event
from clients.models import OIDCClient
from console.permissions import IsIAMAdmin
from core.responses import error_response, success_response
from core.zitadel import zitadel
from rbac.models import Role

logger = logging.getLogger("iam.console.systems")


def _roles_for(system_code: str) -> list[dict]:
    return [
        {"id": str(r.id), "role_id": r.role_id, "name": r.name, "is_admin": r.is_admin,
         "deprecated": r.is_deprecated}
        for r in Role.objects.filter(system_code=system_code).order_by("role_id")
    ]


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def systems_list(request):
    """All onboarded systems with their role catalogues."""
    data = []
    for c in OIDCClient.objects.exclude(system_code="").order_by("system_code"):
        data.append({
            "system_code": c.system_code,
            "name": c.name,
            "client_id": c.client_id,
            "zitadel_project_id": c.zitadel_project_id,
            "lifecycle_state": c.lifecycle_state,
            "redirect_uris": c.redirect_uris,
            "roles": _roles_for(c.system_code),
        })
    return success_response(data=data)


def _system_or_error(system_code):
    client = OIDCClient.objects.filter(system_code=system_code).exclude(zitadel_project_id="").first()
    if not client:
        return None, error_response(message="unknown system", status_code=404)
    return client, None


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def system_roles(request, system_code: str):
    client, err = _system_or_error(system_code)
    if err:
        return err

    if request.method == "GET":
        return success_response(data=_roles_for(system_code))

    role_id = (request.data.get("role_id") or "").strip()
    name = (request.data.get("name") or role_id).strip()
    is_admin = bool(request.data.get("is_admin", False))
    if not role_id:
        return error_response(message="role_id required", status_code=400)

    zitadel().ensure_project_role(client.zitadel_project_id, role_id, name, group=system_code)
    role, _ = Role.objects.update_or_create(
        system_code=system_code, role_id=role_id, version=1,
        defaults={"name": name, "is_admin": is_admin, "owner_system": system_code, "is_deprecated": False},
    )
    emit_event(actor_user_id=str(request.user.id), action="role.created",
               entity_type="role", entity_id=str(role.id), channel="console",
               metadata={"system": system_code, "role_id": role_id})
    return success_response(data={"id": str(role.id), "role_id": role_id}, status_code=201)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def system_role_detail(request, system_code: str, role_id: str):
    client, err = _system_or_error(system_code)
    if err:
        return err
    role = Role.objects.filter(system_code=system_code, role_id=role_id).first()
    if not role:
        return error_response(message="role not found", status_code=404)

    # Remove from ZITADEL (also clears it from any grants) and deprecate locally.
    zitadel().remove_project_role(client.zitadel_project_id, role_id)
    role.is_deprecated = True
    role.save(update_fields=["is_deprecated", "updated_at"])
    emit_event(actor_user_id=str(request.user.id), action="role.deprecated",
               entity_type="role", entity_id=str(role.id), channel="console",
               metadata={"system": system_code, "role_id": role_id})
    return success_response(data={"id": str(role.id)}, message="role deprecated")


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def system_role_check(request, system_code: str):
    """Toggle whether a role grant is required to enter the system (projectRoleCheck)."""
    client, err = _system_or_error(system_code)
    if err:
        return err
    enabled = bool(request.data.get("enabled", True))
    zitadel().set_project_role_check(client.zitadel_project_id, enabled)
    emit_event(actor_user_id=str(request.user.id), action="system.role_check_set",
               entity_type="oidc_client", entity_id=str(client.id), channel="console",
               metadata={"system": system_code, "enabled": enabled})
    return success_response(data={"system_code": system_code, "role_check": enabled})
