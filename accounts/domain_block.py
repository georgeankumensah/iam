"""Disposable email domain block-list for self-registration.

Based on the ``disposable-email-domains`` public dataset (mirrored at
``DISPOSABLE_DOMAIN_LIST_PATH``).  Falls back to a minimal built-in set
when the file is absent.
"""

from pathlib import Path

from django.conf import settings

_BUILTIN_BLOCKED: set[str] = {
    "mailinator.com", "guerrillamail.com", "sharklasers.com",
    "temp-mail.org", "10minutemail.com", "throwaway.email",
    "yopmail.com", "trashmail.com", "maildrop.cc",
    "getnada.com", "tempmail.com", "tempmail.net",
}


def _load_domain_list() -> set[str]:
    path = getattr(settings, "DISPOSABLE_DOMAIN_LIST_PATH", "")
    if path:
        try:
            return {line.strip().lower() for line in Path(path).read_text().splitlines() if line.strip()}
        except FileNotFoundError:
            pass
    return _BUILTIN_BLOCKED


_BLOCKED: set[str] | None = None


def is_disposable_domain(email: str) -> bool:
    global _BLOCKED
    if _BLOCKED is None:
        _BLOCKED = _load_domain_list()
    try:
        domain = email.split("@")[1].lower()
        return domain in _BLOCKED
    except IndexError:
        return False
