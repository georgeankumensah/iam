import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from jose.exceptions import JWSError

from oidc_rp.auth import verify_jwt_token

logger = logging.getLogger("iam.oidc.backchannel")


@csrf_exempt
@require_POST
def backchannel_logout(request):
    logout_token = request.POST.get("logout_token", "")
    if not logout_token:
        logger.warning("Backchannel logout missing logout_token")
        return JsonResponse({"error": "missing_token"}, status=400)

    try:
        payload = verify_jwt_token(logout_token)
        sub = payload.get("sub", "")
        sid = payload.get("sid", "")
        events = payload.get("events", {})

        if "http://schemas.openid.net/event/backchannel-logout" not in events:
            return JsonResponse({"error": "invalid_event"}, status=400)

        from accounts.models import User
        from audit.models import ActiveSession

        try:
            user = User.objects.get(zitadel_user_id=sub)
            ActiveSession.objects.filter(user=user).update(revoked=True)
            logger.info("Backchannel logout processed for user %s (sid=%s)", sub, sid)
        except User.DoesNotExist:
            logger.warning("Backchannel logout for unknown user %s", sub)
            ActiveSession.objects.filter(jti=sid).update(revoked=True)

        return JsonResponse({"status": "ok"})
    except (JWSError, Exception) as e:
        logger.error("Backchannel logout processing failed: %s", e)
        return JsonResponse({"error": "processing_failed"}, status=500)
