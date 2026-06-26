import base64
import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger("iam.oidc.actions")

# Mirror of the signing key Zitadel uses for the target.  Set via
# ZITADEL_ACTIONS_SIGNING_KEY env var (hex).  If absent, HMAC verification
# is skipped (dev mode).
_ACTIONS_SIGNING_KEY = getattr(settings, "ZITADEL_ACTIONS_SIGNING_KEY", "")


def _verify_hmac(body: bytes, signature_header: str) -> bool:
    if not _ACTIONS_SIGNING_KEY:
        return True
    expected = hmac.new(
        bytes.fromhex(_ACTIONS_SIGNING_KEY),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def _decode_metadata(metadata: dict | None) -> dict:
    """Actions V2 sends user_metadata values as base64-encoded strings."""
    if not metadata:
        return {}
    decoded = {}
    for item in metadata:
        if isinstance(item, dict) and "key" in item and "value" in item:
            try:
                decoded[item["key"]] = base64.b64decode(item["value"]).decode()
            except Exception:
                decoded[item["key"]] = item["value"]
    return decoded


def _compute_claims(user_grants: list | None, metadata: dict,
                    client_id: str = "") -> list[dict]:
    """Build the ``append_claims`` response for the Zitadel Actions target.

    Injects ``user_type``, ``portal_access[]``, and ``permissions[]``
    into every issued token.  If a ``client_id`` is provided, claims are
    filtered by the client's ``claim_allow_list``.
    """
    from clients.models import OIDCClient

    claims: list[dict] = []

    user_type = metadata.get("user_type", "")
    if user_type:
        claims.append({"key": "user_type", "value": user_type})

    portal_systems: set[str] = set()
    permissions: set[str] = set()

    for grant in user_grants or []:
        roles = grant.get("roleKeys", [])
        for role_key in roles:
            portal_systems.add(grant.get("projectId", ""))
            permissions.add(f"{grant.get('projectId', '')}:{role_key}")

    if portal_systems:
        claims.append({"key": "portal_access", "value": list(portal_systems)})
    if permissions:
        claims.append({"key": "permissions", "value": list(permissions)})

    if not client_id:
        return claims

    try:
        client = OIDCClient.objects.filter(client_id=client_id).first()
        allow_list = set(client.claim_allow_list) if client and client.claim_allow_list else set()
        if allow_list:
            claims = [c for c in claims if c["key"] in allow_list]
    except Exception:
        logger.warning("Failed to resolve claim allow-list for client %s", client_id)

    return claims


@csrf_exempt
@require_POST
def complement_token(request):
    try:
        body = request.body
        sig = request.META.get("HTTP_ZITADEL_SIGNATURE", "")

        if not _verify_hmac(body, sig):
            logger.warning("Actions V2 HMAC verification failed")
            return JsonResponse(
                {"forwardedStatusCode": 401, "forwardedErrorMessage": "invalid signature"},
                status=200,
            )

        payload = json.loads(body)
        function_type = payload.get("function", "")
        if function_type != "preaccesstoken":
            logger.warning("Unexpected Actions V2 function: %s", function_type)
            return JsonResponse({"append_claims": []}, status=200)

        user_grants = payload.get("user_grants", [])
        user_metadata_raw = payload.get("user_metadata", [])
        metadata = _decode_metadata(user_metadata_raw)
        client_id = (payload.get("userinfo") or {}).get("azp", "")

        claims = _compute_claims(user_grants, metadata, client_id)

        token_json = json.dumps({"append_claims": claims})
        from core.metrics import zitadel_token_size_bytes

        zitadel_token_size_bytes.labels(token_type="access").set(len(token_json))

        return JsonResponse({"append_claims": claims}, status=200)

    except Exception as e:
        logger.error("Actions V2 complement_token error: %s", e)
        return JsonResponse(
            {"forwardedStatusCode": 500, "forwardedErrorMessage": "internal error"},
            status=200,
        )
