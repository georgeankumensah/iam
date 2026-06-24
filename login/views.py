import json
import logging

from django.conf import settings
from django.contrib.auth import login as django_login
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
    code = request.GET.get("code")
    if code:
        return _handle_authorization_code(request, code)
    auth_request = request.GET.get("authRequest", "")
    from .zitadel_auth import ZitadelAuthService
    service = ZitadelAuthService()
    zitadel_callback = f"{service.base_url}/oauth/v2/callback?authRequest={auth_request}"
    return redirect(zitadel_callback)


def _exchange_code_for_tokens(code: str, redirect_uri: str) -> dict | None:
    import urllib.request, urllib.parse
    from urllib.error import HTTPError

    token_url = settings.OIDC_OP_TOKEN_ENDPOINT.rstrip("/")
    parsed = urllib.parse.urlparse(token_url)
    payload = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": settings.OIDC_RP_CLIENT_ID,
    })
    if settings.OIDC_RP_CLIENT_SECRET:
        payload += "&client_secret=" + urllib.parse.quote(settings.OIDC_RP_CLIENT_SECRET)

    req = urllib.request.Request(
        token_url,
        data=payload.encode(),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "localhost:8080",
        },
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read().decode())
    except HTTPError as e:
        logger.error("Token exchange failed: %s %s", e.code, e.read().decode()[:200])
        return None
    except Exception as e:
        logger.error("Token exchange failed: %s", e)
        return None


def _handle_authorization_code(request, code: str):
    redirect_uri = request.build_absolute_uri(request.path)
    token_data = _exchange_code_for_tokens(code, redirect_uri)
    if not token_data:
        return redirect(f"{_LOGIN_APP_URL}/error?error=token_exchange_failed")

    id_token = token_data.get("id_token")
    if not id_token:
        logger.error("No id_token in token response")
        return redirect(f"{_LOGIN_APP_URL}/error?error=no_id_token")

    from uuid import UUID
    from jose import jwt as jose_jwt
    from jose.exceptions import JOSEError
    from accounts.models import User
    try:
        claims = jose_jwt.get_unverified_claims(id_token)
        sub = claims.get("sub", "")
        email = claims.get("email", "")
        zitadel_uuid = UUID(int=int(sub))
        try:
            user = User.objects.get(zitadel_user_id=zitadel_uuid)
        except User.DoesNotExist:
            user = User.objects.create(
                zitadel_user_id=zitadel_uuid,
                email=email,
                user_type="external",
                status="active",
            )
        if user.status == "active":
            django_login(request, user)
            return redirect(settings.LOGIN_REDIRECT_URL or "/")
        else:
            return redirect(f"{_LOGIN_APP_URL}/error?error=account_disabled")
    except JOSEError as e:
        logger.error("ID token validation failed: %s", e)
        return redirect(f"{_LOGIN_APP_URL}/error?error=invalid_id_token")
