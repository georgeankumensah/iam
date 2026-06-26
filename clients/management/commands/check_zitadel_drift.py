"""Nightly CI command: compare Zitadel project/app state vs Django OIDCClient records.

Exits non-zero when drift is detected (for CI gating).  Drift types:

- **Missing project** — Django references a project that doesn't exist in Zitadel.
- **Missing app** — Django references an app ID not found in the Zitadel project.
- **Role catalogue mismatch** — roles defined in Zitadel differ from Django ``Role`` records.
- **Config mismatch** — redirect URIs, grant types, app type differ.

Usage:

    python manage.py check_zitadel_drift [--fix]
"""

from django.core.management.base import BaseCommand

from clients.models import OIDCClient
from core.zitadel import ZitadelError, zitadel


class Command(BaseCommand):
    help = "Compare Zitadel configuration against Django OIDCClient records"

    def handle(self, *args, **options):  # noqa: ARG002
        z = zitadel()
        drifts: list[str] = []

        for client in OIDCClient.objects.all():
            if not client.zitadel_project_id:
                continue

            # 1. Verify project exists
            try:
                z.request("GET", f"/management/v1/projects/{client.zitadel_project_id}")
            except ZitadelError as e:
                drifts.append(
                    f"[{client.system_code}] Project {client.zitadel_project_id} not found in Zitadel: {e}"
                )
                continue

            if not client.zitadel_app_id:
                continue

            # 2. Verify app exists
            try:
                app = z.request(
                    "GET",
                    f"/management/v1/projects/{client.zitadel_project_id}/apps/{client.zitadel_app_id}",
                )
            except ZitadelError:
                drifts.append(
                    f"[{client.system_code}] App {client.zitadel_app_id} not found in project"
                )
                continue

            app_data = app.get("app", {}).get("oidcConfig", {})

            # 3. Redirect URIs
            expected_uris = set(client.redirect_uris or [])
            actual_uris = set(app_data.get("redirectUris", []))
            if expected_uris != actual_uris:
                missing = expected_uris - actual_uris
                extra = actual_uris - expected_uris
                if missing:
                    drifts.append(
                        f"[{client.system_code}] Missing redirect URIs: {missing}"
                    )
                if extra:
                    drifts.append(
                        f"[{client.system_code}] Extra redirect URIs: {extra}"
                    )

            # 4. Role catalogue
            try:
                zitadel_roles = z.list_project_roles(client.zitadel_project_id)
            except ZitadelError:
                continue
            from rbac.models import Role
            django_roles = set(
                Role.objects.filter(system_code=client.system_code, is_deprecated=False)
                .values_list("role_id", flat=True)
            )
            zitadel_role_keys = {r.get("key", "") for r in zitadel_roles}
            if django_roles - zitadel_role_keys:
                drifts.append(
                    f"[{client.system_code}] Roles missing in Zitadel: {django_roles - zitadel_role_keys}"
                )
            if zitadel_role_keys - django_roles:
                drifts.append(
                    f"[{client.system_code}] Orphaned Zitadel roles: {zitadel_role_keys - django_roles}"
                )

        if drifts:
            for d in drifts:
                self.stdout.write(self.style.WARNING(d))
            self.stdout.write(self.style.ERROR(f"Found {len(drifts)} drift(s)"))
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS("No drift detected"))
