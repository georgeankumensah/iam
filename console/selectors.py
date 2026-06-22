from accounts.models import User


def list_users(user_type: str | None = None, status: str | None = None, search: str | None = None):
    qs = User.objects.all()

    if user_type:
        qs = qs.filter(user_type=user_type)
    if status:
        qs = qs.filter(status=status)
    if search:
        qs = qs.filter(email__icontains=search)

    return qs.order_by("-created_at")
