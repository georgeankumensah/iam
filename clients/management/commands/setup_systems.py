"""Provision each downstream system as its own ZITADEL project + SPA app + roles.

Idempotent. For every system it:
  - creates the ZITADEL project (role assertion + role check on),
  - creates the SPA (PKCE) app if missing → client_id,
  - ensures the project roles (admin/user),
  - mirrors them into the Django rbac.Role catalogue and clients.OIDCClient.

Run: docker compose exec django python manage.py setup_systems
Then copy each printed client_id into the matching SPA's src/lib/oidc.ts.
"""

import time

from django.conf import settings
from django.core.management.base import BaseCommand

from clients.services import provision_system, redirect_uris_for_port
from core.zitadel import ZitadelError, zitadel

# Role keys MUST match exactly what each downstream system reads from the token.
# is_admin marks the single "system administrator" role (used for delegated
# invites); other elevated roles are still just normal grants to IAM.
SYSTEMS = [
    {
        "code": "ams",  # System 07 — Accreditation Management System
        "project": "AMS",
        "app": "AMS SPA",
        "frontend_port": 5173,
        "roles": [
            ("institution_contact", "Institution Primary Contact", False),
            ("accreditation_officer", "Accreditation Officer", False),
            ("inspector", "Inspector", False),
            ("directorate_lead", "Directorate Lead", False),
            ("board_member", "CLET Board Member", False),
            ("director_general", "Director General", False),
            ("case_manager", "Appeals / Case Manager", False),
            ("admin", "System Administrator", True),
        ],
    },
    {
        "code": "nbes",  # System 10A — National Bar Examination System
        "project": "NBES",
        "app": "NBES SPA",
        "frontend_port": 5174,
        "roles": [
            ("nbec_member", "NBEC Member", False),
            ("nbec_secretariat", "NBEC Secretariat", False),
            ("item_writer", "Item Writer", False),
            ("moderator", "Moderator", False),
            ("examiner", "Examiner", False),
            ("clet_registrar", "CLET Registrar", False),
            ("candidate", "Candidate", False),
            ("auditor", "Auditor", False),
            ("system_administrator", "System Administrator", True),
        ],
    },
    {
        "code": "gov",  # System 11 — Governance Portal
        "project": "GOV",
        "app": "GOV SPA",
        "frontend_port": 5175,
        "roles": [
            ("director_general", "Director-General", False),
            ("registrar", "Registrar / Council Secretary", False),
            ("board_member", "Board Member", False),
            ("board_chair", "Board Chair", False),
            ("compliance_officer", "Compliance Officer", False),
            ("internal_auditor", "Internal Auditor", False),
            ("system_administrator", "System Administrator", True),
        ],
    },
    {
        "code": "nlems",  # System 01 — National Legal Education Management System
        "project": "NLEMS",
        "app": "NLEMS SPA",
        "frontend_port": 5176,
        "roles": [
            ("nlems_student", "Student", False),
            ("nlems_institution_registrar", "Institution Registrar", False),
            ("nlems_lpt_coordinator", "LPT Coordinator", False),
            ("nlems_lpt_supervisor", "LPT Supervisor", False),
            ("nlems_verification_officer", "Verification Officer", False),
            ("nlems_director_general", "Director General", False),
            ("nlems_clet_registrar", "CLET Registrar", False),
            ("nlems_auditor", "Auditor", False),
            ("nlems_api_consumer", "API Consumer", False),
            ("nlems_system_admin", "System Administrator", True),
        ],
    },
]


class Command(BaseCommand):
    help = "Provision each system as its own ZITADEL project + app + roles."

    def add_arguments(self, parser):
        # Used when run automatically at container start: wait for ZITADEL to be
        # reachable, and never fail the boot if it isn't.
        parser.add_argument("--wait", type=int, default=0, help="seconds to wait for ZITADEL")
        parser.add_argument("--best-effort", action="store_true", help="don't error if ZITADEL is unreachable")

    def _wait_for_zitadel(self, seconds: int) -> bool:
        deadline = time.monotonic() + seconds
        while True:
            try:
                zitadel()._access_token()
                return True
            except Exception:  # noqa: BLE001
                if time.monotonic() >= deadline:
                    return False
                time.sleep(3)

    def handle(self, *_args, **options):
        if options["wait"] and not self._wait_for_zitadel(options["wait"]):
            msg = "ZITADEL not reachable; skipping setup_systems (re-run later)."
            if options["best_effort"]:
                self.stdout.write(self.style.WARNING(msg))
                return
            raise ZitadelError(0, msg)

        for sys_def in SYSTEMS:
            redirects, logout = redirect_uris_for_port(sys_def["frontend_port"])
            try:
                res = provision_system(
                    code=sys_def["code"],
                    project_name=sys_def["project"],
                    app_name=sys_def["app"],
                    redirect_uris=redirects,
                    post_logout_uris=logout,
                    roles=sys_def["roles"],
                )
            except Exception as exc:  # noqa: BLE001
                if options["best_effort"]:
                    self.stdout.write(self.style.WARNING(f"[{sys_def['code']}] skipped: {exc}"))
                    continue
                raise
            self.stdout.write(self.style.SUCCESS(
                f"[{sys_def['code']}] project={res['project_id']} "
                f"app={res['app_id']} client_id={res['client_id']}"
            ))
            self._grant_bootstrap_admin(sys_def["code"])

        self.stdout.write("\nUpdate each SPA's src/lib/oidc.ts CLIENT_ID with the value above.")

    def _grant_bootstrap_admin(self, system_code: str) -> None:
        email = settings.BOOTSTRAP_ZITADEL_ADMIN_EMAIL
        if not email:
            return

        from accounts.models import User, UserStatus
        from rbac.models import Role, RoleBinding
        from rbac.services import sync_user_system_grant

        z = zitadel()
        z_user = z.find_user_by_email(email)
        if not z_user:
            self.stdout.write(self.style.WARNING(f"[{system_code}] bootstrap admin not found in ZITADEL: {email}"))
            return

        user, _ = User.objects.update_or_create(
            email=email,
            defaults={
                "zitadel_user_id": z_user["userId"],
                "user_type": "staff",
                "status": UserStatus.ACTIVE,
                "is_staff": True,
                "is_superuser": True,
            },
        )

        role = Role.objects.filter(system_code=system_code, is_admin=True, is_deprecated=False).first()
        if not role:
            self.stdout.write(self.style.WARNING(f"[{system_code}] no admin role to grant to {email}"))
            return

        RoleBinding.objects.get_or_create(
            role=role,
            user=user,
            state=RoleBinding.BindingState.APPROVED,
            defaults={"approver": user, "justification": "Bootstrap ZITADEL superadmin"},
        )
        sync_user_system_grant(user, system_code)
