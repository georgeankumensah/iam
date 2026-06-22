from rest_framework.permissions import BasePermission


class IsIAMAdmin(BasePermission):
    def has_permission(self, request, view):  # noqa: ARG002
        return bool(request.user and request.user.is_authenticated and request.user.user_type == "staff")


class IsDG(BasePermission):
    def has_permission(self, request, view):  # noqa: ARG002
        return bool(request.user and request.user.is_authenticated and hasattr(request.user, "role_bindings"))
