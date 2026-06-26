import hashlib
import hmac
import logging

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger("iam.lifecycle.hrms")

HRMS_WEBHOOK_SECRET = settings.SECRET_KEY


@csrf_exempt
@require_POST
def hrms_webhook(request):
    body = request.body
    signature = request.META.get("HTTP_X_HUB_SIGNATURE_256", "")

    expected = hmac.new(HRMS_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(f"sha256={expected}", signature):
        return JsonResponse({"error": "invalid_signature"}, status=401)

    import json
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)

    event_type = payload.get("event_type", "")

    from .models import HrmsEvent
    from .tasks import handle_hrms_event

    event = HrmsEvent.objects.create(
        event_type=event_type,
        target_email=payload.get("email", ""),
        payload=payload,
        signature_valid=True,
        status=HrmsEvent.Status.RECEIVED,
    )
    handle_hrms_event.delay(event_type, payload, event_id=str(event.id))

    return JsonResponse({"status": "queued", "event_id": str(event.id)})
