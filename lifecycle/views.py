from functools import wraps

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from .scim import UserProvisionerBackend


def scim_auth_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        token = getattr(settings, "SCIM_BEARER_TOKEN", "")
        if not token:
            return Response({"error": "unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
        auth = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth.startswith("Bearer ") or auth.removeprefix("Bearer ") != token:
            return Response({"error": "unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
        return view_func(request, *args, **kwargs)
    return wrapper

provisioner = UserProvisionerBackend()


@api_view(["POST"])
@authentication_classes([])
@permission_classes([])
@scim_auth_required
def scim_create_user(request):  # noqa: ARG001
    from accounts.models import User

    email = request.data.get("userName", request.data.get("emails", [{}])[0].get("value", ""))
    first_name = request.data.get("name", {}).get("givenName", "")
    last_name = request.data.get("name", {}).get("familyName", "")

    zitadel_result = provisioner.create_user(email=email, first_name=first_name, last_name=last_name)
    if not zitadel_result:
        return Response({"error": "provisioning_failed"}, status=status.HTTP_502_BAD_GATEWAY)

    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            "zitadel_user_id": zitadel_result.get("userId"),
            "status": "pre_active",
        },
    )
    return Response({"id": str(user.id), "zitadel_user_id": str(user.zitadel_user_id)}, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
@authentication_classes([])
@permission_classes([])
@scim_auth_required
def scim_user_detail(request, user_id: str):
    from accounts.models import User

    try:
        user = User.objects.get(id=user_id)

        if request.method == "GET":
            return Response({
                "id": str(user.id),
                "userName": user.email,
                "emails": [{"value": user.email, "primary": True}],
                "active": user.status == "active",
                "meta": {"resourceType": "User"},
            })

        elif request.method == "PATCH":
            email = request.data.get("userName", request.data.get("emails", [{}])[0].get("value", ""))
            if email:
                user.email = email
            user.metadata = {**user.metadata, **request.data.get("metadata", {})}
            user.save()
            return Response({"status": "updated"})

        elif request.method == "DELETE":
            if user.zitadel_user_id:
                provisioner.deactivate_user(str(user.zitadel_user_id))
            user.status = "disabled"
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

    except User.DoesNotExist:
        return Response({"error": "not_found"}, status=status.HTTP_404_NOT_FOUND)
