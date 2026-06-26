import logging
from typing import Any

from django.conf import settings
from jose import jwk, jwt
from jose.exceptions import ExpiredSignatureError, JWSError, JWTClaimsError
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

logger = logging.getLogger("iam.oidc.auth")


def _fetch_jwks() -> list[dict[str, Any]]:
    import requests
    resp = requests.get(settings.OIDC_OP_JWKS_ENDPOINT, timeout=10)
    resp.raise_for_status()
    return resp.json().get("keys", [])


def verify_jwt_token(
    token: str,
    audience: str | None = None,
    issuer: str | None = None,
) -> dict[str, Any]:
    """Verify a JWT from ZITADEL using the JWKS endpoint.

    Returns the decoded payload on success, raises on failure.
    """
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")

    jwks = _fetch_jwks()
    signing_key = None
    for key in jwks:
        if key.get("kid") == kid:
            signing_key = key
            break

    if not signing_key:
        raise JWSError("No matching signing key found in JWKS")

    public_key = jwk.construct(signing_key)
    payload = jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        audience=[audience or settings.OIDC_RP_CLIENT_ID],
        issuer=issuer or settings.ZITADEL_HOST,
        options={"verify_exp": True, "verify_at_hash": False},
    )
    return payload


class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request: Request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header.removeprefix("Bearer ")
        try:
            payload = verify_jwt_token(token)
            user = self._get_user(payload)
            return (user, payload)
        except AuthenticationFailed:
            raise
        except Exception as e:
            logger.error("JWT authentication error: %s", e)
            raise AuthenticationFailed("Invalid token") from e

    def authenticate_header(self, request):  # noqa: ARG002
        return 'Bearer realm="iam"'

    def _get_user(self, payload: dict[str, Any]):
        from accounts.models import User

        sub = payload.get("sub", "")
        email = payload.get("email", "")
        zitadel_user_id = sub

        try:
            user = User.objects.get(zitadel_user_id=zitadel_user_id)
        except User.DoesNotExist:
            if not settings.OIDC_CREATE_USER:
                raise AuthenticationFailed("User not found") from None
            user = User.objects.create(
                zitadel_user_id=zitadel_user_id,
                email=email,
                user_type=payload.get("user_type", "external"),
                status="active",
            )

        if user.status != "active":
            raise AuthenticationFailed("User account is disabled") from None

        return user
