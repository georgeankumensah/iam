from django.contrib.auth import logout
from django.shortcuts import redirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


def logout_view(request):
    id_token_hint = request.GET.get("id_token_hint", "")
    state = request.GET.get("state", "")
    post_logout_redirect = request.GET.get("post_logout_redirect_uri", "/")

    from django.conf import settings
    end_session_url = settings.OIDC_OP_LOGOUT_ENDPOINT
    params = f"?id_token_hint={id_token_hint}&post_logout_redirect_uri={post_logout_redirect}&state={state}"

    logout(request)
    return redirect(end_session_url + params)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request):
    user = request.user
    return Response({
        "id": str(user.id),
        "email": user.email,
        "user_type": user.user_type,
        "status": user.status,
        "metadata": user.metadata,
    })
