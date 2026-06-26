from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from accounts.models import User
from audit.models import AuditEvent
from console.permissions import IsIAMAdmin
from core.responses import success_response
from delegation.models import Delegation
from rbac.models import RoleBinding


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def admin_dashboard(request):  # noqa: ARG001
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    users = User.objects.all()
    total_users = users.count()
    users_by_type = {t: users.filter(user_type=t).count() for t, _ in User.UserType.choices}
    users_by_status = {s: users.filter(status=s).count() for s, _ in User.UserStatus.choices}

    pending_bindings = RoleBinding.objects.filter(state=RoleBinding.BindingState.REQUESTED).count()

    active_delegations = Delegation.objects.filter(state=Delegation.DelegationState.ACTIVE).count()

    audit_24h = AuditEvent.objects.filter(timestamp__gte=today_start).count()

    pending_reviews = (
        RoleBinding.objects.filter(state=RoleBinding.BindingState.REQUESTED).count()
    )

    return success_response(data={
        "total_users": total_users,
        "users_by_type": users_by_type,
        "users_by_status": users_by_status,
        "pending_role_bindings": pending_bindings,
        "active_delegations": active_delegations,
        "audit_events_24h": audit_24h,
        "pending_access_reviews": pending_reviews,
    })
