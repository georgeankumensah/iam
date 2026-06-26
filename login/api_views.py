import logging

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from accounts.domain_block import is_disposable_domain

from .risk import login_risk_scorer
from .zitadel_auth import MFA_FACTOR_SMS, MFA_FACTOR_TOTP, MFA_FACTOR_WEBAUTHN, ZitadelAuthService

logger = logging.getLogger("iam.login.api")

auth_service = ZitadelAuthService()


@api_view(["POST"])
def register(request):
    email = request.data.get("email", "").strip().lower()
    if not email:
        return Response(
            {"error": "missing_email", "error_description": "Email is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if is_disposable_domain(email):
        return Response(
            {"error": "disposable_domain", "error_description": "Disposable email domains are not allowed"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    from accounts.models import User

    if User.objects.filter(email=email).exists():
        return Response(
            {"error": "email_exists", "error_description": "An account with this email already exists"},
            status=status.HTTP_409_CONFLICT,
        )

    user_type = request.data.get("user_type", "public")
    if user_type not in ("student", "external", "public"):
        user_type = "public"

    user = User.objects.create(
        email=email,
        user_type=user_type,
        status=User.UserStatus.PENDING,
    )

    from core.zitadel import zitadel

    try:
        zitadel_user_id = zitadel().create_human_user(email, email.split("@")[0], "")
        user.zitadel_user_id = zitadel_user_id
        user.save(update_fields=["zitadel_user_id"])
    except Exception as e:
        logger.error("Failed to create Zitadel user for %s: %s", email, e)
        user.delete()
        return Response(
            {"error": "provisioning_failed", "error_description": "Could not create account"},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    return Response({"email": email, "status": "pending"}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def login_auth(request):
    email = request.data.get("email", "")
    password = request.data.get("password", "")
    auth_request = request.data.get("authRequest", "")

    if not email or not password:
        return Response(
            {"error": "missing_fields", "error_description": "Email and password are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    zitadel_user = auth_service.get_user_by_email(email)
    if not zitadel_user:
        return Response(
            {"error": "invalid_credentials", "error_description": "Invalid email or password"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    verify_result = auth_service.verify_password(zitadel_user["id"], password)
    if not verify_result.success:
        return Response(
            {"error": verify_result.error, "error_description": verify_result.error_description or "Authentication failed"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    ip_address = request.META.get("REMOTE_ADDR", "")
    user_agent = request.META.get("HTTP_USER_AGENT", "")
    risk = login_risk_scorer.assess(ip_address=ip_address, user_agent=user_agent)
    if risk.requires_denial:
        return Response(
            {"error": "high_risk", "error_description": "Authentication denied due to risk assessment"},
            status=status.HTTP_403_FORBIDDEN,
        )

    session_result = auth_service.create_session(zitadel_user["id"], auth_request)
    if not session_result.success:
        return Response(
            {"error": "server_error", "error_description": "Could not create session"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    data = {
        "session_id": session_result.session_id,
        "mfa_required": session_result.mfa_required,
        "mfa_factors": session_result.mfa_factors or [],
        "consent_required": session_result.consent_required,
        "redirect_url": None,
    }
    if not session_result.mfa_required and not session_result.consent_required:
        data["redirect_url"] = _build_callback_url(auth_request)

    return Response(data)


@api_view(["POST"])
def mfa_verify(request, factor: str):
    session_id = request.data.get("sessionId", "")
    auth_request = request.data.get("authRequest", "")
    code = request.data.get("code", "")

    if factor == MFA_FACTOR_TOTP:
        result = auth_service.verify_totp(session_id, code)
    elif factor == MFA_FACTOR_WEBAUTHN:
        result = auth_service.verify_webauthn(session_id, request.data.get("credential", {}))
    elif factor == MFA_FACTOR_SMS:
        result = auth_service.verify_sms(session_id, code)
    else:
        return Response(
            {"error": "invalid_factor", "error_description": "Unsupported MFA factor"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not result.success:
        return Response(
            {"error": result.error, "error_description": result.error_description or "Verification failed"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    return Response({"session_id": session_id, "redirect_url": f"/login/consent?authRequest={auth_request}"})


@api_view(["POST"])
def consent_grant(request):
    auth_request = request.data.get("authRequest", "")
    approve = request.data.get("approve", True)

    result = auth_service.grant_consent(auth_request, approve=bool(approve))
    if not result.success:
        return Response(
            {"error": "consent_failed", "error_description": "Could not process consent"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    redirect_url = result.redirect_url or _build_callback_url(auth_request)
    return Response({"redirect_url": redirect_url})


@api_view(["POST"])
def password_reset(request):
    email = request.data.get("email", "")
    if email:
        auth_service.trigger_password_reset(email)
    return Response({"sent": True})


@api_view(["GET"])
def login_callback(request):
    auth_request = request.query_params.get("authRequest", "")
    return Response({"redirect_url": _build_callback_url(auth_request)})


def _build_callback_url(auth_request: str) -> str:
    return f"{auth_service.base_url}/oauth/v2/callback?authRequest={auth_request}"
