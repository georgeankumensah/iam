"""Admin views over delegations (IAM-F04). Ingress/auto-expiry live in the
delegation app; these let an admin list and revoke."""

import logging

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from audit.emit import emit_event
from console.permissions import IsIAMAdmin
from core.responses import error_response, paginated_response, success_response

logger = logging.getLogger("iam.console.delegations")


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def delegations_list(request):
    from delegation.models import Delegation

    qs = Delegation.objects.select_related("delegator", "delegate", "role").order_by("-created_at")
    state = request.query_params.get("state")
    if state:
        qs = qs.filter(state=state)

    def serialize(items):
        return [{
            "id": str(d.id),
            "delegator": d.delegator.email,
            "delegate": d.delegate.email,
            "system_code": d.role.system_code,
            "role_id": d.role.role_id,
            "state": d.state,
            "start_at": d.start_at,
            "end_at": d.end_at,
        } for d in items]

    return paginated_response(request, qs, serialize)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def delegation_revoke(request, delegation_id: str):
    from delegation.models import Delegation
    from rbac.models import RoleBinding
    from rbac.services import sync_user_system_grant

    try:
        d = Delegation.objects.select_related("delegate", "role").get(id=delegation_id)
    except Delegation.DoesNotExist:
        return error_response(message="not_found", status_code=404)
    if d.state != Delegation.DelegationState.ACTIVE:
        return error_response(message="not_active", status_code=409)

    d.state = Delegation.DelegationState.REVOKED
    d.save(update_fields=["state", "updated_at"])

    # Revoke the delegated role binding and re-evaluate the delegate's access.
    RoleBinding.objects.filter(
        user=d.delegate, role=d.role, state=RoleBinding.BindingState.APPROVED
    ).update(state=RoleBinding.BindingState.REVOKED)
    sync_user_system_grant(d.delegate, d.role.system_code, reevaluate_sessions=True)

    emit_event(actor_user_id=str(request.user.id), action="delegation.revoked",
               entity_type="delegation", entity_id=str(d.id), channel="console")
    return success_response(data={"id": str(d.id)}, message="delegation revoked")
