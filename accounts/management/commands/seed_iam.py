import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger("iam.management.seed")


class Command(BaseCommand):
    help = "Seed the IAM database with initial roles and admin user"

    def handle(self, *args, **options):
        from accounts.models import User, ZitadelUserSync
        from audit.emit import emit_event
        from rbac.models import Role, RoleBinding

        admin_email = settings.BOOTSTRAP_ADMIN_EMAIL

        user, created = User.objects.get_or_create(
            email=admin_email,
            defaults={
                "user_type": "staff",
                "status": "active",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            ZitadelUserSync.objects.create(user=user, sync_status="bootstrap")
            self.stdout.write(self.style.SUCCESS(f"Created admin user: {admin_email}"))
        else:
            self.stdout.write(f"Admin user already exists: {admin_email}")

        roles_data = [
            {
                "system_code": "IAM",
                "role_id": "iam_admin",
                "name": "IAM Administrator",
                "description": "Full access to IAM console",
                "permission_strings": [
                    "iam:users:read",
                    "iam:users:write",
                    "iam:roles:read",
                    "iam:roles:write",
                    "iam:clients:read",
                    "iam:clients:write",
                    "iam:audit:read",
                    "iam:audit:export",
                ],
            },
            {
                "system_code": "IAM",
                "role_id": "system_owner",
                "name": "System Owner",
                "description": "Read-only access to IAM resources",
                "permission_strings": [
                    "iam:users:read",
                    "iam:roles:read",
                    "iam:audit:read",
                ],
            },
            {
                "system_code": "IAM",
                "role_id": "auditor",
                "name": "Auditor",
                "description": "Audit log access and export",
                "permission_strings": [
                    "iam:audit:read",
                    "iam:audit:export",
                ],
            },
            {
                "system_code": "IAM",
                "role_id": "operator",
                "name": "Operator",
                "description": "Day-to-day operations",
                "permission_strings": [
                    "iam:users:read",
                    "iam:roles:read",
                    "iam:clients:read",
                    "iam:delegation:read",
                ],
            },
            {
                "system_code": "GSL",
                "role_id": "gsl_admin",
                "name": "GSL Administrator",
                "description": "Full access to GSL resources",
                "permission_strings": [
                    "gsl:*",
                ],
            },
        ]

        role_map = {}
        for rd in roles_data:
            role, created = Role.objects.get_or_create(
                system_code=rd["system_code"],
                role_id=rd["role_id"],
                version=1,
                defaults={
                    "name": rd["name"],
                    "description": rd.get("description", ""),
                    "permission_strings": rd["permission_strings"],
                    "effective_from": timezone.now(),
                },
            )
            role_map[rd["role_id"]] = role
            if created:
                self.stdout.write(f"  Created role: {role}")

        admin_role = role_map.get("iam_admin")
        if admin_role:
            binding, created = RoleBinding.objects.get_or_create(
                role=admin_role,
                user=user,
                defaults={
                    "state": RoleBinding.BindingState.EFFECTIVE,
                    "approver": user,
                    "effective_from": timezone.now(),
                    "justification": "Bootstrap seed",
                },
            )
            if created:
                self.stdout.write(f"  Bound {user.email} to {admin_role}")

        emit_event(
            actor_user_id=str(user.id),
            actor_email=user.email,
            action="system.seeded",
            entity_type="system",
            channel="bootstrap",
            metadata={"admin_email": admin_email},
        )
        self.stdout.write(self.style.SUCCESS("IAM seed complete"))
