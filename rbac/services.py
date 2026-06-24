"""Role-binding → ZITADEL user-grant synchronisation.

IAM owns role *identity*; ZITADEL carries the granted roles into tokens as
`urn:zitadel:iam:org:project:roles`. Whenever a user's bindings for a system
change, we recompute the union and push it as a single user grant on that
system's project (or remove it when none remain).
"""

from __future__ import annotations

import logging

from django.utils import timezone

from clients.models import OIDCClient
from core.zitadel import zitadel
from rbac.models import RoleBinding

logger = logging.getLogger("iam.rbac.services")


class SoDViolation(Exception):
    """Raised when a role would breach a separation-of-duties rule."""


def check_sod(user, role) -> None:
    """Reject mutually-exclusive role combinations before binding.

    A RuleDefinition with predicate_json
    {"type": "mutually_exclusive", "roles": ["IAM:auditor", "IAM:iam_admin"]}
    means a user may hold at most one role from that set.
    """
    from rbac.models import RoleBinding, RuleDefinition

    key = f"{role.system_code}:{role.role_id}"
    held = {
        f"{b.role.system_code}:{b.role.role_id}"
        for b in RoleBinding.objects.filter(
            user=user, state=RoleBinding.BindingState.APPROVED
        ).select_related("role")
    }
    for rule in RuleDefinition.objects.filter(enabled=True):
        pred = rule.predicate_json or {}
        if pred.get("type") != "mutually_exclusive":
            continue
        group = set(pred.get("roles", []))
        if key in group and (held & (group - {key})):
            raise SoDViolation(rule.name)


def project_id_for_system(system_code: str) -> str | None:
    client = (
        OIDCClient.objects.filter(system_code=system_code)
        .exclude(zitadel_project_id="")
        .first()
    )
    return client.zitadel_project_id if client else None


def active_role_keys(user, system_code: str) -> list[str]:
    now = timezone.now()
    qs = RoleBinding.objects.filter(
        user=user,
        role__system_code=system_code,
        state=RoleBinding.BindingState.APPROVED,
    ).select_related("role")
    keys: list[str] = []
    for b in qs:
        if b.effective_to and b.effective_to < now:
            continue
        if b.effective_from and b.effective_from > now:
            continue
        keys.append(b.role.role_id)
    return sorted(set(keys))


def sync_user_system_grant(user, system_code: str, reevaluate_sessions: bool = False) -> None:
    """Push the user's current role set for one system to ZITADEL.

    Creates/updates the grant to match active bindings, or removes it when the
    user has no remaining roles for that system.
    """
    if not user.zitadel_user_id:
        logger.warning("sync_user_system_grant: user %s has no zitadel_user_id", user.id)
        return
    project_id = project_id_for_system(system_code)
    if not project_id:
        logger.warning("sync_user_system_grant: no project for system %s", system_code)
        return

    z = zitadel()
    uid = str(user.zitadel_user_id)
    keys = active_role_keys(user, system_code)

    if keys:
        z.upsert_user_grant(uid, project_id, keys)
    else:
        existing = z.find_user_grant(uid, project_id)
        if existing:
            z.remove_user_grant(uid, existing["id"])

    if reevaluate_sessions:
        # Role removal/change should not keep stale access alive.
        z.terminate_user_sessions(uid)
