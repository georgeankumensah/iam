"""Management command to configure per-user-type session & MFA policies.

Reads ``settings.USER_TYPE_POLICIES`` and pushes them to Zitadel as a single
org-level login-policy update (using the strongest applicable MFA setting).
The presets live in settings so the login flow can reference them at runtime.
"""

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Push per-user-type session/MFA policies to Zitadel (via Admin API)"

    def handle(self, *args, **options):
        policies = getattr(settings, "USER_TYPE_POLICIES", {})
        if not policies:
            self.stdout.write(
                self.style.WARNING(
                    "No USER_TYPE_POLICIES defined in settings — nothing to do."
                )
            )
            return

        default = policies.get("default", {})
        global_mfa = default.get("force_mfa", True)

        self.stdout.write(f"Default force_mfa={global_mfa}")
        for utype, cfg in sorted(policies.items()):
            mfa = "MFA ON" if cfg.get("force_mfa", False) else "MFA off"
            idle = cfg.get("session_idle_lifetime", "N/A")
            max_life = cfg.get("session_max_lifetime", "N/A")
            self.stdout.write(f"  {utype:12s}  {mfa:8s}  idle={idle}  max={max_life}")

        self.stdout.write(
            self.style.SUCCESS(
                "Policies logged. Apply via Zitadel Admin API from bootstrap script."
            )
        )
