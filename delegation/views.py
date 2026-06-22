import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Delegation, DelegationWebhookEvent

logger = logging.getLogger("iam.delegation")


@csrf_exempt
@require_POST
def webhook(request):
    body = request.body
    signature = request.META.get("HTTP_X_SIGNATURE", "")

    if not signature:
        return JsonResponse({"error": "missing_signature"}, status=401)

    import json
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)

    DelegationWebhookEvent.objects.create(
        event_type=payload.get("event_type", "unknown"),
        payload=payload,
        signature=signature,
    )

    event_type = payload.get("event_type")
    if event_type == "delegation.grant":
        return _handle_grant(payload)
    elif event_type == "delegation.revoke":
        return _handle_revoke(payload)
    else:
        return JsonResponse({"status": "received"})


def _handle_grant(payload: dict) -> JsonResponse:
    from accounts.models import User
    from rbac.models import Role

    delegator_id = payload.get("delegator_user_id")
    delegate_id = payload.get("delegate_user_id")
    role_id = payload.get("role_id")
    start_at = payload.get("start_at")
    end_at = payload.get("end_at")
    justification = payload.get("justification", "")

    try:
        delegator = User.objects.get(zitadel_user_id=delegator_id)
        delegate = User.objects.get(zitadel_user_id=delegate_id)
        role = Role.objects.get(id=role_id)

        Delegation.objects.create(
            delegator=delegator,
            delegate=delegate,
            role=role,
            start_at=start_at,
            end_at=end_at,
            justification=justification,
        )
        return JsonResponse({"status": "granted"})
    except (User.DoesNotExist, Role.DoesNotExist) as e:
        logger.error("Delegation grant failed: %s", e)
        return JsonResponse({"error": "not_found"}, status=404)


def _handle_revoke(payload: dict) -> JsonResponse:
    delegation_id = payload.get("delegation_id")
    try:
        delegation = Delegation.objects.get(id=delegation_id, state=Delegation.DelegationState.ACTIVE)
        delegation.state = Delegation.DelegationState.REVOKED
        delegation.save(update_fields=["state"])
        return JsonResponse({"status": "revoked"})
    except Delegation.DoesNotExist:
        return JsonResponse({"error": "not_found"}, status=404)
