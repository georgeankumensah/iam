"""System (OIDC client) provisioning — the single source of truth.

Used by both the `setup_systems` management command (declarative seed of the
known systems) and the admin console API (ad-hoc creation of new systems). Each
"system" is its own ZITADEL project + SPA app + role set, mirrored into Django
(rbac.Role + clients.OIDCClient).
"""

from __future__ import annotations

import logging

from clients.models import ClientLifecycleState, OIDCClient
from core.zitadel import zitadel
from rbac.models import Role

logger = logging.getLogger("iam.clients.services")


def redirect_uris_for_port(port: int) -> tuple[list[str], list[str]]:
    import os
    scheme_host = os.environ.get("PUBLIC_CLIENT_BASE_URL", "http://localhost")
    base = f"{scheme_host}:{port}"
    return (
        [f"{base}/login/callback", f"{base}/auth/callback"],
        [f"{base}/login", base],
    )


def provision_system(
    *,
    code: str,
    project_name: str,
    redirect_uris: list[str],
    post_logout_uris: list[str],
    roles: list[tuple[str, str, bool]],
    app_name: str | None = None,
) -> dict:
    """Idempotently provision a system in ZITADEL + Django.

    roles: list of (role_key, display_name, is_admin).
    Returns {client_id, project_id, app_id}.
    """
    z = zitadel()
    app_name = app_name or f"{project_name} SPA"

    project_id = z.get_or_create_project(project_name)

    app = z.find_app_by_name(project_id, app_name)
    if app:
        client_id = app.get("oidcConfig", {}).get("clientId") or app.get("clientId", "")
        app_id = app.get("id", "")
    else:
        created = z.create_spa_app(project_id, app_name, redirect_uris, post_logout_uris)
        client_id, app_id = created["clientId"], created["appId"]

    for key, display, is_admin in roles:
        z.ensure_project_role(project_id, key, display, group=code)
        Role.objects.update_or_create(
            system_code=code, role_id=key, version=1,
            defaults={"name": display, "is_admin": is_admin, "owner_system": code, "is_deprecated": False},
        )

    obj, _ = OIDCClient.objects.update_or_create(
        client_id=client_id,
        defaults={
            "system_code": code,
            "name": project_name,
            "zitadel_project_id": project_id,
            "zitadel_app_id": app_id,
            "redirect_uris": redirect_uris,
            "post_logout_redirect_uris": post_logout_uris,
            "lifecycle_state": ClientLifecycleState.PRODUCTION_LIVE,
        },
    )

    return {"id": str(obj.id), "client_id": client_id, "project_id": project_id, "app_id": app_id}
