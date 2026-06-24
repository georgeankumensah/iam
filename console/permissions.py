from rest_framework.permissions import BasePermission


class IsIAMAdmin(BasePermission):
    def has_permission(self, request, view):  # noqa: ARG002
        return bool(request.user and request.user.is_authenticated and request.user.user_type == "staff")


class IsDG(BasePermission):
    def has_permission(self, request, view):  # noqa: ARG002
        return bool(request.user and request.user.is_authenticated and hasattr(request.user, "role_bindings"))


def is_iam_admin(user) -> bool:
    """Global IAM administrator: superuser, or holder of the IAM admin role."""
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    from rbac.models import RoleBinding
    return RoleBinding.objects.filter(
        user=user,
        role__system_code__iexact="IAM",
        role__role_id="iam_admin",
        state=RoleBinding.BindingState.APPROVED,
    ).exists()


def is_system_admin(user, system_code: str) -> bool:
    """Admin of a specific system: holds that system's admin-tier role."""
    if not getattr(user, "is_authenticated", False):
        return False
    from rbac.models import RoleBinding
    return RoleBinding.objects.filter(
        user=user,
        role__system_code=system_code,
        role__is_admin=True,
        state=RoleBinding.BindingState.APPROVED,
    ).exists()


def can_manage_system_invites(user, system_code: str) -> bool:
    """IAM admins manage any system; a system admin manages their own system."""
    return is_iam_admin(user) or is_system_admin(user, system_code)
