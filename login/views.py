import base64
import json
import logging
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth import login as django_login
from django.shortcuts import redirect

logger = logging.getLogger("iam.login")

_LOGIN_APP_URL = settings.LOGIN_APP_BASE_URL


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


def complete_view(request):
    """Complete OIDC after the custom login-app has verified password + MFA.

    The login-app stores the ZITADEL session in a host-scoped HTTP-only cookie.
    Since local apps share the `localhost` host, Django can read the same cookie,
    ask ZITADEL to finish the auth request, and then redirect the browser to the
    originating app callback URL.
    """
    auth_request = request.GET.get("authRequest", "")
    if not auth_request:
        return redirect(f"{_LOGIN_APP_URL}/error?error=missing_auth_request")

    raw_cookie = request.COOKIES.get("zitadel-session")
    session = _parse_zitadel_session_cookie(raw_cookie)
    if not session:
        logger.warning(
            "complete_view: no valid session cookie. raw=%s len=%s has_cookie=%s",
            (raw_cookie or "")[:60],
            len(raw_cookie or ""),
            bool(raw_cookie),
        )
        return redirect(f"{_LOGIN_APP_URL}/login?authRequest={auth_request}")

    from core.zitadel import ZitadelError, zitadel

    z = zitadel()
    try:
        callback_url = z.create_oidc_callback(auth_request, session["id"], session["token"])
    except ZitadelError as e:
        if "GrantRequired" in e.body:
            callback_url = _retry_after_syncing_user_grants(z, auth_request, session)
            if callback_url:
                return redirect(callback_url)
            logger.warning(
                "OIDC completion denied after grant sync: auth_request=%s user_id=%s",
                auth_request,
                session.get("userId", ""),
            )
            return redirect(f"{_LOGIN_APP_URL}/signedin?authRequest={auth_request}&error=access_denied")
        logger.error("OIDC completion failed: %s", e)
        return redirect(f"{_LOGIN_APP_URL}/error?error=oidc_completion_failed")

    if not callback_url:
        return redirect(f"{_LOGIN_APP_URL}/error?error=missing_callback_url")
    return redirect(callback_url)


def _b64url_decode(s: str) -> bytes:
    """Decode unpadded base64url (compatible with Node.js toString('base64url'))."""
    s = s.replace("-", "+").replace("_", "/")
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.b64decode(s)


def _decrypt_session_cookie(encoded: str) -> dict | None:
    """Decrypt an AES-256-GCM encrypted session cookie (iv:tag:ciphertext).
    Compatible with login-app's Node.js crypto implementation.
    """
    import hashlib

    secret = settings.SESSION_ENCRYPTION_KEY
    if not secret:
        return None
    parts = encoded.split(":")
    if len(parts) != 3:
        return None
    try:
        key = hashlib.sha256(secret.encode()).digest()
        iv = _b64url_decode(parts[0])
        tag = _b64url_decode(parts[1])
        ciphertext = _b64url_decode(parts[2])
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(iv, ciphertext + tag, None)
        return json.loads(plaintext.decode("utf-8"))
    except Exception:
        return None


def _parse_zitadel_session_cookie(cookie_value: str | None) -> dict | None:
    if not cookie_value:
        return None
    # Try new encrypted format first
    parsed = _decrypt_session_cookie(cookie_value)
    if parsed:
        return parsed
    # Fall back to legacy base64 format
    try:
        padded = cookie_value + "=" * (-len(cookie_value) % 4)
        data = json.loads(base64.b64decode(padded).decode("utf-8"))
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
    if not all(data.get(key) for key in ("id", "token")):
        return None
    return data


def _retry_after_syncing_user_grants(zitadel_service, auth_request: str, session: dict) -> str:
    user_id = session.get("userId")
    if not user_id:
        return ""

    from accounts.models import User
    from core.zitadel import ZitadelError
    from rbac.models import RoleBinding
    from rbac.services import sync_user_system_grant

    user = User.objects.filter(zitadel_user_id=user_id).first()
    if not user:
        return ""

    system_codes = (
        RoleBinding.objects.filter(user=user, state=RoleBinding.BindingState.APPROVED)
        .exclude(role__system_code="")
        .values_list("role__system_code", flat=True)
        .distinct()
    )
    for system_code in system_codes:
        sync_user_system_grant(user, system_code)

    try:
        return zitadel_service.create_oidc_callback(auth_request, session["id"], session["token"])
    except ZitadelError:
        return ""


def _exchange_code_for_tokens(code: str, redirect_uri: str) -> dict | None:
    import urllib.parse
    import urllib.request
    from urllib.error import HTTPError

    token_url = settings.OIDC_OP_TOKEN_ENDPOINT.rstrip("/")
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
            "Host": settings.ZITADEL_EXTERNAL_DOMAIN,
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

    from jose.exceptions import JWSError

    from accounts.models import User
    from oidc_rp.auth import verify_jwt_token
    try:
        claims = verify_jwt_token(id_token)
        sub = claims.get("sub", "")
        email = claims.get("email", "")
        try:
            user = User.objects.get(zitadel_user_id=sub)
        except User.DoesNotExist:
            user = User.objects.create(
                zitadel_user_id=sub,
                email=email,
                user_type="external",
                status="active",
            )
        if user.status == "active":
            django_login(request, user)
            access_token = token_data.get("access_token", "")
            state = request.GET.get("state", "")
            parsed = urlparse(state)
            redirect_url = state if parsed.scheme else (settings.LOGIN_REDIRECT_URL or "/")
            if access_token:
                request.session["admin_token"] = access_token
            return redirect(redirect_url)
        else:
            return redirect(f"{_LOGIN_APP_URL}/error?error=account_disabled")
    except (JWSError, Exception) as e:
        logger.error("ID token validation failed: %s", e)
        return redirect(f"{_LOGIN_APP_URL}/error?error=invalid_id_token")
