from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from accounts.models import User
from clients.models import OIDCClient
from console.permissions import IsIAMAdmin
from core.responses import success_response
from rbac.models import RoleBinding


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsIAMAdmin])
def rbac_matrix(request):
    systems = OIDCClient.objects.exclude(system_code="").values_list("system_code", flat=True).distinct()

    system_filter = request.query_params.get("system_code")
    user_type_filter = request.query_params.get("user_type")

    users_qs = User.objects.filter(status=User.UserStatus.ACTIVE)
    if user_type_filter:
        users_qs = users_qs.filter(user_type=user_type_filter)

    rows = []
    for user in users_qs:
        row = {"user_id": str(user.id), "email": user.email, "user_type": user.user_type}
        bindings = RoleBinding.objects.filter(
            user=user,
            state=RoleBinding.BindingState.APPROVED,
        ).select_related("role")

        roles_by_system: dict[str, list[str]] = {}
        for b in bindings:
            if b.effective_to and b.effective_to < timezone.now():
                continue
            if b.effective_from and b.effective_from > timezone.now():
                continue
            code = b.role.system_code
            roles_by_system.setdefault(code, []).append(b.role.role_id)

        if system_filter:
            row["roles"] = {system_filter: roles_by_system.get(system_filter, [])}
            if not roles_by_system.get(system_filter):
                continue
        else:
            row["roles"] = roles_by_system

        rows.append(row)

    return success_response(data={
        "systems": list(systems),
        "matrix": rows,
    })
