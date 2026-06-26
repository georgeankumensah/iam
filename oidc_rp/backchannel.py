import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger("iam.oidc.backchannel")


@csrf_exempt
@require_POST
def backchannel_logout(request):
    logout_token = request.POST.get("logout_token", "")
    if not logout_token:
        logger.warning("Backchannel logout missing logout_token")
        return JsonResponse({"error": "missing_token"}, status=400)

    try:
        from jose import jwt as jose_jwt
        payload = jose_jwt.get_unverified_claims(logout_token)
        sub = payload.get("sub", "")
        sid = payload.get("sid", "")
        events = payload.get("events", {})

        if "http://schemas.openid.net/event/backchannel-logout" not in events:
            return JsonResponse({"error": "invalid_event"}, status=400)

        from accounts.models import User
        from audit.emit import emit_event
        from audit.models import ActiveSession

        _SENTINEL_UID = "00000000-0000-0000-0000-000000000000"
        try:
            user = User.objects.get(zitadel_user_id=sub)
            revoked = ActiveSession.objects.filter(user=user).update(revoked=True)
            logger.info("Backchannel logout processed for user %s (sid=%s)", sub, sid)
            emit_event(actor_user_id=str(user.id), actor_email=user.email,
                       action="oidc.backchannel_logout", entity_type="session", entity_id=sid,
                       channel="oidc", result="success", metadata={"sessions_revoked": revoked})
        except User.DoesNotExist:
            logger.warning("Backchannel logout for unknown user %s", sub)
            ActiveSession.objects.filter(jti=sid).update(revoked=True)
            emit_event(actor_user_id=_SENTINEL_UID, action="oidc.backchannel_logout",
                       entity_type="session", entity_id=sid, channel="oidc", result="success",
                       metadata={"note": "user_not_local"})

        return JsonResponse({"status": "ok"})
    except Exception as e:
        logger.error("Backchannel logout processing failed: %s", e)
        try:
            from core.metrics import backchannel_logout_failures_total
            backchannel_logout_failures_total.inc()
        except Exception:  # noqa: BLE001
            pass
        try:
            from audit.emit import emit_event
            emit_event(actor_user_id=_SENTINEL_UID, action="oidc.logout_delivery_failure",
                       entity_type="session", entity_id="", channel="oidc", result="failure",
                       metadata={"error": str(e)})
        except Exception:  # noqa: BLE001
            logger.exception("Failed to emit LogoutDeliveryFailure audit event")
        return JsonResponse({"error": "processing_failed"}, status=500)
