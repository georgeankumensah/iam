from .base import *  # noqa: F403, F405

DEBUG = False

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "staging.iam.clet.gov.gh").split(",")  # noqa: F405

DATABASES["default"]["NAME"] = os.environ.get("DB_NAME", "iam_staging")  # noqa: F405

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
