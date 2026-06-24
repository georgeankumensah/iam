import logging

from django.conf import settings
from django.shortcuts import redirect

logger = logging.getLogger("iam.login")

_LOGIN_APP_URL = "http://localhost:3000"


def _login_app_redirect(request):
    query = request.META.get("QUERY_STRING", "")
    target = f"{_LOGIN_APP_URL}{request.path}?{query}" if query else f"{_LOGIN_APP_URL}{request.path}"
    return redirect(target)


login_view = _login_app_redirect
mfa_view = _login_app_redirect
consent_view = _login_app_redirect
password_reset_view = _login_app_redirect
error_view = _login_app_redirect


def callback_view(request):
    auth_request = request.GET.get("authRequest", "")
    from .zitadel_auth import ZitadelAuthService
    service = ZitadelAuthService()
    zitadel_callback = f"{service.base_url}/oauth/v2/callback?authRequest={auth_request}"
    return redirect(zitadel_callback)
