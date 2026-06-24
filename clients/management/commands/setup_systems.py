"""Provision each downstream system as its own ZITADEL project + SPA app + roles.

Idempotent. For every system it:
  - creates the ZITADEL project (role assertion + role check on),
  - creates the SPA (PKCE) app if missing → client_id,
  - ensures the project roles (admin/user),
  - mirrors them into the Django rbac.Role catalogue and clients.OIDCClient.

Run: docker compose exec django python manage.py setup_systems
Then copy each printed client_id into the matching SPA's src/lib/oidc.ts.
"""

from django.core.management.base import BaseCommand

from clients.models import ClientLifecycleState, OIDCClient
from core.zitadel import zitadel
from rbac.models import Role

SYSTEMS = [
    {
        "code": "ams",
        "project": "AMS",
        "app": "AMS SPA",
        "redirects": ["http://localhost:5173/login/callback", "http://localhost:5173/auth/callback"],
        "logout": ["http://localhost:5173/login", "http://localhost:5173"],
        "roles": [
            ("admin", "AMS Administrator", True),
            ("user", "AMS User", False),
        ],
    },
    {
        "code": "nbes",
        "project": "NBES",
        "app": "NBES SPA",
        "redirects": ["http://localhost:5174/login/callback", "http://localhost:5174/auth/callback"],
        "logout": ["http://localhost:5174/login", "http://localhost:5174"],
        "roles": [
            ("admin", "NBES Administrator", True),
            ("user", "NBES User", False),
        ],
    },
]


class Command(BaseCommand):
    help = "Provision each system as its own ZITADEL project + app + roles."

    def handle(self, *args, **options):
        z = zitadel()
        for sys_def in SYSTEMS:
            code = sys_def["code"]
            project_id = z.get_or_create_project(sys_def["project"])

            app = z.find_app_by_name(project_id, sys_def["app"])
            if app:
                client_id = app.get("oidcConfig", {}).get("clientId") or app.get("clientId", "")
                app_id = app.get("id", "")
            else:
                created = z.create_spa_app(project_id, sys_def["app"], sys_def["redirects"], sys_def["logout"])
                client_id, app_id = created["clientId"], created["appId"]

            for key, display, is_admin in sys_def["roles"]:
                z.ensure_project_role(project_id, key, display, group=code)
                Role.objects.update_or_create(
                    system_code=code, role_id=key, version=1,
                    defaults={"name": display, "is_admin": is_admin, "owner_system": code},
                )

            OIDCClient.objects.update_or_create(
                client_id=client_id,
                defaults={
                    "system_code": code,
                    "name": sys_def["project"],
                    "zitadel_project_id": project_id,
                    "zitadel_app_id": app_id,
                    "redirect_uris": sys_def["redirects"],
                    "post_logout_redirect_uris": sys_def["logout"],
                    "lifecycle_state": ClientLifecycleState.PRODUCTION_LIVE,
                },
            )

            self.stdout.write(self.style.SUCCESS(
                f"[{code}] project={project_id} app={app_id} client_id={client_id}"
            ))

        self.stdout.write("\nUpdate each SPA's src/lib/oidc.ts CLIENT_ID with the value above.")
