from .base import *  # noqa: F403, F405

DEBUG = False

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "iam.clet.gov.gh").split(",")  # noqa: F405

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
        "json": {"class": "core.logging.JsonLogHandler"},
    },
    "root": {"handlers": ["console", "json"], "level": "INFO"},
}
