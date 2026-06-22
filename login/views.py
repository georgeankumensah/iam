import logging

from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .risk import login_risk_scorer
from .zitadel_auth import MFA_FACTOR_SMS, MFA_FACTOR_TOTP, MFA_FACTOR_WEBAUTHN, ZitadelAuthService

logger = logging.getLogger("iam.login")

auth_service = ZitadelAuthService()


@require_http_methods(["GET", "POST"])
def login_view(request):
    auth_request = request.GET.get("authRequest", request.POST.get("authRequest", ""))
    error = request.GET.get("error", "")
    error_description = request.GET.get("error_description", "")

    if request.method == "POST":
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")

        if not username or not password:
            return render(request, "login/login.html", {
                "auth_request": auth_request,
                "error": "missing_fields",
                "error_description": "Email and password are required",
            })

        user = auth_service.get_user_by_email(username)
        if not user:
            return render(request, "login/login.html", {
                "auth_request": auth_request,
                "error": "invalid_credentials",
                "error_description": "Invalid email or password",
            })

        result = auth_service.verify_password(user["id"], password)
        if not result.success:
            return render(request, "login/login.html", {
                "auth_request": auth_request,
                "error": result.error,
                "error_description": result.error_description or "Authentication failed",
            })

        ip_address = request.META.get("REMOTE_ADDR", "")
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        risk = login_risk_scorer.assess(ip_address=ip_address, user_agent=user_agent)
        if risk.requires_denial:
            return render(request, "login/login.html", {
                "auth_request": auth_request,
                "error": "high_risk",
                "error_description": "Authentication denied due to risk assessment",
            })

        session_result = auth_service.create_session(user["id"], auth_request)
        if not session_result.success:
            return render(request, "login/login.html", {
                "auth_request": auth_request,
                "error": "server_error",
                "error_description": "Could not create session",
            })

        if session_result.mfa_required and session_result.mfa_factors:
            factor = session_result.mfa_factors[0]
            return redirect(f"/login/mfa/{factor}?authRequest={auth_request}&sessionId={session_result.session_id}")

        if session_result.consent_required:
            return redirect(f"/login/consent?authRequest={auth_request}")

        return redirect(f"/login/callback?authRequest={auth_request}")

    return render(request, "login/login.html", {
        "auth_request": auth_request,
        "error": error,
        "error_description": error_description,
    })


@require_http_methods(["GET", "POST"])
def mfa_view(request, factor: str):
    auth_request = request.GET.get("authRequest", "")
    session_id = request.POST.get("sessionId", request.GET.get("sessionId", ""))

    if request.method == "POST":
        if factor == MFA_FACTOR_TOTP:
            code = request.POST.get("code", "")
            result = auth_service.verify_totp(session_id, code)
        elif factor == MFA_FACTOR_WEBAUTHN:
            result = auth_service.verify_webauthn(session_id, {})
        elif factor == MFA_FACTOR_SMS:
            code = request.POST.get("code", "")
            result = auth_service.verify_sms(session_id, code)
        else:
            return render(request, "login/error.html", {"error": "invalid_factor", "error_description": "Unsupported MFA factor"})

        if not result.success:
            template_map = {
                MFA_FACTOR_TOTP: "login/mfa_totp.html",
                MFA_FACTOR_WEBAUTHN: "login/mfa_webauthn.html",
                MFA_FACTOR_SMS: "login/mfa_sms.html",
            }
            return render(request, template_map.get(factor, "login/error.html"), {
                "auth_request": auth_request,
                "session_id": session_id,
                "error": result.error,
                "error_description": result.error_description or "Verification failed",
            })

        return redirect(f"/login/consent?authRequest={auth_request}")

    template_map = {
        MFA_FACTOR_TOTP: "login/mfa_totp.html",
        MFA_FACTOR_WEBAUTHN: "login/mfa_webauthn.html",
        MFA_FACTOR_SMS: "login/mfa_sms.html",
    }
    return render(request, template_map.get(factor, "login/error.html"), {
        "auth_request": auth_request,
        "session_id": session_id,
    })


@require_http_methods(["GET", "POST"])
def consent_view(request):
    auth_request = request.GET.get("authRequest", request.POST.get("authRequest", ""))

    if request.method == "POST":
        approve = request.POST.get("approve") == "true"
        result = auth_service.grant_consent(auth_request, approve=approve)
        if not result.success:
            return render(request, "login/consent.html", {
                "auth_request": auth_request,
                "error": "consent_failed",
                "error_description": "Could not process consent",
            })
        if result.redirect_url:
            return redirect(result.redirect_url)
        return redirect(f"/login/callback?authRequest={auth_request}")

    return render(request, "login/consent.html", {"auth_request": auth_request})


@require_http_methods(["GET", "POST"])
def password_reset_view(request):
    if request.method == "POST":
        email = request.POST.get("email", "")
        if email:
            auth_service.trigger_password_reset(email)
        return render(request, "login/password_reset.html", {"sent": True})
    return render(request, "login/password_reset.html", {"sent": False})


def error_view(request):
    error = request.GET.get("error", "unknown_error")
    error_description = request.GET.get("error_description", "An unexpected error occurred")
    return render(request, "login/error.html", {"error": error, "error_description": error_description})


def callback_view(request):
    auth_request = request.GET.get("authRequest", "")
    zitadel_callback = f"{auth_service.base_url}/oauth/v2/callback?authRequest={auth_request}"
    return redirect(zitadel_callback)
