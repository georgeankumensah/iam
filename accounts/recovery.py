import hashlib
import hmac
import secrets

from django.conf import settings

RECOVERY_CODE_COUNT = 10
RECOVERY_CODE_BYTES = 10


def _hash_code(code: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode(),
        code.encode(),
        hashlib.sha256,
    ).hexdigest()


def _mask_code(code: str) -> str:
    return code[:4] + "*" * (len(code) - 4)


def generate_recovery_codes(user) -> list[dict]:
    """Generate a fresh set of recovery codes for the user.

    Replaces any existing unused codes.  Returns the plain-text codes (display
    once) alongside their masked versions.
    """
    from .models import RecoveryCode

    RecoveryCode.objects.filter(user=user, used=False).delete()

    codes: list[dict] = []
    for _ in range(RECOVERY_CODE_COUNT):
        plain = secrets.token_hex(RECOVERY_CODE_BYTES)
        masked = _mask_code(plain)

        RecoveryCode.objects.create(
            user=user,
            code_hash=_hash_code(plain),
            masked_code=masked,
        )
        codes.append({"code": plain, "masked": masked})

    return codes


def verify_recovery_code(user, code: str) -> bool:
    """Redeem a single-use recovery code for the user.

    Returns True if the code was valid and is now consumed.
    """
    from .models import RecoveryCode

    code_hash = _hash_code(code)
    entry = RecoveryCode.objects.filter(
        user=user,
        code_hash=code_hash,
        used=False,
    ).first()
    if not entry:
        return False

    entry.used = True
    from django.utils import timezone
    entry.used_at = timezone.now()
    entry.save(update_fields=["used", "used_at"])
    return True


def remaining_codes(user) -> list[dict]:
    """Return masked view of remaining unused codes for the user."""
    from .models import RecoveryCode

    return list(
        RecoveryCode.objects.filter(user=user, used=False).values("id", "masked_code", "created_at")
    )
