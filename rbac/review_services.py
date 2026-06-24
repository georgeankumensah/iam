"""Access-review campaign logic (IAM-F03-03).

Generates review items from current active grants, applies keep/revoke/change-role
decisions (revocations flow through to ZITADEL), and produces a signed report
digest at completion.
"""

from __future__ import annotations

import hashlib
import json
import logging

from django.utils import timezone

from rbac.models import AccessReviewItem, Role, RoleBinding
from rbac.services import sync_user_system_grant

logger = logging.getLogger("iam.rbac.review")


def generate_items(campaign) -> int:
    """Snapshot the active role bindings in scope into review items."""
    qs = RoleBinding.objects.filter(state=RoleBinding.BindingState.APPROVED).select_related("role", "user")
    scope_system = (campaign.scope or {}).get("system_code")
    if scope_system:
        qs = qs.filter(role__system_code=scope_system)

    created = 0
    for b in qs:
        AccessReviewItem.objects.create(
            campaign=campaign, binding=b, user=b.user,
            system_code=b.role.system_code, role_id=b.role.role_id,
        )
        created += 1
    return created


def apply_decision(item, decision: str, reviewer, new_role_id: str = "", note: str = "") -> None:
    """Record and enforce a single review decision."""
    item.decision = decision
    item.reviewer = reviewer
    item.note = note
    item.decided_at = timezone.now()

    if decision == AccessReviewItem.Decision.REVOKE and item.binding:
        item.binding.state = RoleBinding.BindingState.REVOKED
        item.binding.save(update_fields=["state", "updated_at"])
        sync_user_system_grant(item.user, item.system_code, reevaluate_sessions=True)

    elif decision == AccessReviewItem.Decision.CHANGE_ROLE:
        new_role = Role.objects.filter(id=new_role_id, system_code=item.system_code).first()
        if not new_role:
            raise ValueError("new_role_id invalid for this system")
        if item.binding:
            item.binding.state = RoleBinding.BindingState.REVOKED
            item.binding.save(update_fields=["state", "updated_at"])
        RoleBinding.objects.get_or_create(
            role=new_role, user=item.user, state=RoleBinding.BindingState.APPROVED,
            defaults={"approver": reviewer, "justification": f"access review {item.campaign.period}"},
        )
        item.new_role = new_role
        sync_user_system_grant(item.user, item.system_code, reevaluate_sessions=True)

    item.save()


def sign_report(campaign, actor) -> dict:
    """Produce a deterministic, hash-signed report of all decisions.

    The digest is computed over the immutable content (campaign + decisions)
    only, so it is reproducible at completion and on later export. signed_by /
    signed_at are metadata outside the hash.
    """
    items = list(campaign.items.all().order_by("created_at"))
    content = {
        "campaign": {"id": str(campaign.id), "name": campaign.name, "period": campaign.period,
                     "scope": campaign.scope},
        "decisions": [
            {"user": i.user.email, "system_code": i.system_code, "role_id": i.role_id,
             "decision": i.decision, "new_role": i.new_role.role_id if i.new_role else None,
             "reviewer": i.reviewer.email if i.reviewer else None,
             "decided_at": i.decided_at.isoformat() if i.decided_at else None}
            for i in items
        ],
        "counts": decision_counts(campaign),
    }
    digest = hashlib.sha256(
        json.dumps(content, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        **content,
        "digest": digest,
        "signed_by": actor.email if actor else None,
        "signed_at": timezone.now().isoformat(),
    }


def decision_counts(campaign) -> dict:
    counts = {d.value: 0 for d in AccessReviewItem.Decision}
    for item in campaign.items.all():
        counts[item.decision] = counts.get(item.decision, 0) + 1
    return counts
