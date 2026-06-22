from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class IAMError(Exception):
    code: str = "INTERNAL_ERROR"
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    message: str = "An unexpected error occurred"

    def __init__(self, message: str | None = None, detail: str | None = None) -> None:
        self.message = message or self.message
        self.detail = detail


class AuthzDeniedError(IAMError):
    code = "AUTHZ_DENIED"
    status_code = status.HTTP_403_FORBIDDEN
    message = "Authorization denied"


class MFARequiredError(IAMError):
    code = "MFA_REQUIRED"
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Multi-factor authentication required"


class StepUpRequiredError(IAMError):
    code = "STEP_UP_REQUIRED"
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Step-up authentication required"


class MetadataMissingError(IAMError):
    code = "METADATA_MISSING"
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Required metadata is missing"


class RoleConflictError(IAMError):
    code = "ROLE_CONFLICT"
    status_code = status.HTTP_409_CONFLICT
    message = "Role conflict detected"


class RateLimitHitError(IAMError):
    code = "RATE_LIMIT_HIT"
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    message = "Rate limit exceeded"


class NotFoundError(IAMError):
    code = "NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Resource not found"


class ValidationError(IAMError):
    code = "VALIDATION_ERROR"
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Validation failed"


class ConflictError(IAMError):
    code = "CONFLICT"
    status_code = status.HTTP_409_CONFLICT
    message = "Resource conflict"


class TokenReplayError(IAMError):
    code = "TOKEN_REPLAY"
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Token replay detected"


def exception_handler(exc, context):
    if isinstance(exc, IAMError):
        data = {
            "success": False,
            "message": exc.message,
            "data": None,
            "meta": None,
            "errors": {"code": exc.code, "detail": getattr(exc, "detail", None)},
        }
        return Response(data, status=exc.status_code)
    return drf_exception_handler(exc, context)
