from urllib.parse import urlparse

from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from core.responses import error_response, success_response


@api_view(["GET"])
def validate_logout_redirect(request):
    """Check if a redirect_uri is registered in any OIDCClient's
    post_logout_redirect_uris."""
    from clients.models import OIDCClient

    uri = request.GET.get("uri", "")
    if not uri:
        return success_response(data={"valid": False})

    for client in OIDCClient.objects.all():
        for registered in (client.post_logout_redirect_uris or []):
            if uri.rstrip("/") == registered.rstrip("/"):
                return success_response(data={"valid": True})

    return success_response(data={"valid": False})


def logout_view(request):
    id_token_hint = request.GET.get("id_token_hint", "")
    state = request.GET.get("state", "")
    post_logout_redirect = request.GET.get("post_logout_redirect_uri", "/")

    from django.conf import settings
    end_session_url = settings.OIDC_OP_LOGOUT_ENDPOINT
    params = f"?id_token_hint={id_token_hint}&post_logout_redirect_uri={post_logout_redirect}&state={state}"

    logout(request)
    return redirect(end_session_url + params)


def _active_bindings(user):
    from rbac.models import RoleBinding

    now = timezone.now()
    out = []
    for b in RoleBinding.objects.filter(
        user=user, state=RoleBinding.BindingState.APPROVED
    ).select_related("role"):
        if b.effective_to and b.effective_to < now:
            continue
        if b.effective_from and b.effective_from > now:
            continue
        out.append(b)
    return out


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def me_view(request):
    """Self-service profile. GET returns identity + roles; PATCH updates own
    profile metadata/phone (Django-owned fields)."""
    user = request.user

    if request.method == "PATCH":
        if "phone" in request.data:
            user.phone = request.data["phone"]
        if "metadata" in request.data and isinstance(request.data["metadata"], dict):
            user.metadata = {**(user.metadata or {}), **request.data["metadata"]}
        user.save(update_fields=["phone", "metadata", "updated_at"])

    roles = [
        {"system_code": b.role.system_code, "role_id": b.role.role_id, "is_admin": b.role.is_admin}
        for b in _active_bindings(user)
    ]
    return success_response(data={
        "id": str(user.id),
        "email": user.email,
        "phone": user.phone,
        "user_type": user.user_type,
        "status": user.status,
        "metadata": user.metadata,
        "roles": roles,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_apps(request):
    """App switcher: systems this user can open, with role and permissions."""
    from clients.models import OIDCClient

    client_cache: dict[str, OIDCClient | None] = {}

    def _client(code: str):
        if code not in client_cache:
            client_cache[code] = OIDCClient.objects.filter(system_code=code).first()
        return client_cache[code]

    apps = []
    for b in _active_bindings(request.user):
        code = b.role.system_code
        client = _client(code)
        if not client:
            continue
        frontend_url = ""
        for uri in client.redirect_uris or []:
            p = urlparse(uri)
            if p.scheme and p.netloc:
                frontend_url = f"{p.scheme}://{p.netloc}"
                break
        apps.append({
            "system_code": code,
            "system_name": client.name or code,
            "frontend_url": frontend_url,
            "role": b.role.role_id,
            "permissions": b.role.permission_strings,
        })
    apps.sort(key=lambda a: (a["system_code"], a["role"]))
    return success_response(data=apps, message="Available systems retrieved.")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_sessions(request):
    """List the caller's active ZITADEL sessions."""
    from core.zitadel import zitadel

    if not request.user.zitadel_user_id:
        return success_response(data=[])
    sessions = zitadel().list_user_sessions(str(request.user.zitadel_user_id))
    data = [
        {
            "id": s.get("id"),
            "creation_date": s.get("creationDate"),
            "change_date": s.get("changeDate"),
            "user_agent": (s.get("userAgent") or {}).get("description"),
        }
        for s in sessions
    ]
    return success_response(data=data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_token_view(request):
    """One-time retrieval of the admin access_token stored in the session
    during the OIDC code exchange. Cleared after first read to avoid leaking
    through session replay."""
    token = request.session.pop("admin_token", None)
    if not token:
        return error_response(message="no admin token available", status_code=404)
    return success_response(data={"access_token": token})


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def terminate_my_session(request, session_id: str):
    """Terminate one of the caller's own sessions."""
    from core.zitadel import zitadel

    if not request.user.zitadel_user_id:
        return error_response(message="no sessions", status_code=404)
    z = zitadel()
    owned = {s.get("id") for s in z.list_user_sessions(str(request.user.zitadel_user_id))}
    if session_id not in owned:
        return error_response(message="not your session", status_code=404)
    z.delete_session(session_id)
    return success_response(data={"id": session_id}, message="session terminated")
