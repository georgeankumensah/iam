import os
from pathlib import Path

from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "insecure-dev-key-change-in-prod")

DEBUG = False

ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "drf_spectacular",
    "corsheaders",
    "core",
    "accounts",
    "login",
    "oidc_rp",
    "clients",
    "rbac",
    "delegation",
    "pam",
    "lifecycle",
    "audit",
    "compliance",
    "console",
    "api.auth",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.RateLimitMiddleware",
    "core.middleware.CorrelationIdMiddleware",
    "core.middleware.MetricsMiddleware",
    "core.middleware.SecurityHeadersMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "iam"),
        "USER": os.environ.get("DB_USER", "iam"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"sslmode": os.environ.get("DB_SSLMODE", "prefer")},
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en"

TIME_ZONE = "Africa/Accra"

USE_I18N = True

USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "oidc_rp.auth.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "core.renderers.UnifiedEnvelopeRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "PAGE_SIZE": 50,
    "EXCEPTION_HANDLER": "core.exceptions.exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "IAM System 19 API",
    "DESCRIPTION": "Centralised Identity, Authentication, Authorisation & Access-Control Platform",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
        "core.schema.add_health_endpoints",
    ],
}

CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",") if os.environ.get("CORS_ALLOWED_ORIGINS") else []
CORS_ALLOW_CREDENTIALS = True

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Africa/Accra"
CELERY_BEAT_SCHEDULE: dict[str, object] = {
    "expire-invitations": {
        "task": "accounts.tasks.expire_invitations",
        "schedule": 3600.0,
    },
    "expire-delegations": {
        "task": "delegation.tasks.expire_delegations",
        "schedule": 60.0,
    },
    "forward-audit-outbox": {
        "task": "audit.forwarder.forward_outbox",
        "schedule": 300.0,
    },
    "anchor-chain-daily": {
        "task": "audit.tasks.anchor_chain_daily",
        "schedule": crontab(hour=2, minute=0),  # 02:00 Africa/Accra
    },
    "activate-pre-active-accounts": {
        "task": "lifecycle.tasks.activate_pre_active_accounts",
        "schedule": 3600.0,
    },
    "finalize-leaver-disable": {
        "task": "lifecycle.tasks.finalize_leaver_disable",
        "schedule": 3600.0,
    },
    "purge-unverified-registrations": {
        "task": "lifecycle.tasks.purge_unverified_registrations",
        "schedule": crontab(hour=3, minute=0),  # 03:00 Africa/Accra
    },
    "rotate-due-client-secrets": {
        "task": "clients.tasks.rotate_due_client_secrets",
        "schedule": crontab(hour=3, minute=30),  # 03:30 Africa/Accra
    },
    "execute-overdue-access-review-revocations": {
        "task": "rbac.tasks.execute_overdue_access_review_revocations",
        "schedule": crontab(hour=4, minute=0),  # 04:00 Africa/Accra
    },
    "notify-dg-24h-before-expiry": {
        "task": "delegation.tasks.notify_dg_24h_before_expiry",
        "schedule": 3600.0,
    },
    "cleanup-expired-auth-sessions": {
        "task": "api.auth.tasks.cleanup_expired_auth_sessions",
        "schedule": 3600.0,
    },
    "anchor-pam-recording-hashes": {
        "task": "pam.tasks.anchor_recording_hashes_daily",
        "schedule": crontab(hour=2, minute=30),  # 02:30 Africa/Accra
    },
    "cleanup-stale-pam-sessions": {
        "task": "pam.tasks.cleanup_stale_pam_sessions",
        "schedule": 3600.0,
    },
    "cleanup-expired-active-sessions": {
        "task": "audit.tasks.cleanup_expired_active_sessions",
        "schedule": 3600.0,
    },
    "collect-db-connection-metrics": {
        "task": "core.tasks.collect_db_connection_metrics",
        "schedule": 60.0,
    },
    "collect-pam-session-metrics": {
        "task": "core.tasks.collect_pam_session_metrics",
        "schedule": 60.0,
    },
}

ZITADEL_HOST = os.environ.get("ZITADEL_HOST", "https://zitadel.iam.clet.gov.gh")
ZITADEL_PROJECT_ID = os.environ.get("ZITADEL_PROJECT_ID", "")
ZITADEL_ORG_ID = os.environ.get("ZITADEL_ORG_ID", "")
ZITADEL_SERVICE_ACCOUNT_JWT = os.environ.get("ZITADEL_SERVICE_ACCOUNT_JWT", "")
# Machine-key (service account) used by the Django ZITADEL service client for the
# JWT-bearer grant, plus the instance's external domain sent as the Host header
# so ZITADEL resolves the right instance.
ZITADEL_MACHINE_KEY_PATH = os.environ.get("ZITADEL_MACHINE_KEY_PATH", "/machinekey/zitadel-admin-sa.json")
ZITADEL_EXTERNAL_DOMAIN = os.environ.get("ZITADEL_EXTERNAL_DOMAIN", "localhost:8080")

# Onboarding / invitations
LOGIN_APP_BASE_URL = os.environ.get("LOGIN_APP_BASE_URL", "http://localhost:3000")
ONBOARDING_INTERNAL_SECRET = os.environ.get("ONBOARDING_INTERNAL_SECRET", "change-me-internal")
INVITATION_TTL_HOURS = int(os.environ.get("INVITATION_TTL_HOURS", "168"))

OIDC_RP_CLIENT_ID = os.environ.get("OIDC_RP_CLIENT_ID", "")
OIDC_RP_CLIENT_SECRET = os.environ.get("OIDC_RP_CLIENT_SECRET", "")
OIDC_OP_ISSUER = os.environ.get("OIDC_OP_ISSUER", f"http://{os.environ.get('ZITADEL_EXTERNAL_DOMAIN', 'localhost:8080')}")
OIDC_ALLOWED_AUDIENCES = [
    x.strip()
    for x in os.environ.get("OIDC_ALLOWED_AUDIENCES", OIDC_RP_CLIENT_ID).split(",")
    if x.strip()
]
OIDC_OP_JWKS_ENDPOINT = f"{os.environ.get('ZITADEL_HOST', '')}/oauth/v2/keys"
OIDC_OP_AUTHORIZATION_ENDPOINT = f"{os.environ.get('ZITADEL_HOST', '')}/oauth/v2/authorize"
OIDC_OP_TOKEN_ENDPOINT = f"{os.environ.get('ZITADEL_HOST', '')}/oauth/v2/token"
OIDC_OP_USERINFO_ENDPOINT = f"{os.environ.get('ZITADEL_HOST', '')}/oauth/v2/userinfo"
OIDC_OP_LOGOUT_ENDPOINT = f"{os.environ.get('ZITADEL_HOST', '')}/oauth/v2/end_session"
OIDC_RP_SIGN_ALGO = "RS256"
OIDC_RP_SCOPES = "openid email profile urn:zitadel:iam:org:project:id:zitadel:aud"
OIDC_RP_IDP_SIGN_KEY = None
OIDC_CREATE_USER = True
OIDC_STORE_ACCESS_TOKEN = True
OIDC_STORE_ID_TOKEN = True
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX_ATTEMPTS = 20
RATE_LIMIT_PATHS = ["/login/", "/password-reset/", "/register/"]

DISPOSABLE_DOMAIN_LIST_PATH = os.environ.get("DISPOSABLE_DOMAIN_LIST_PATH", "")

# HMAC signing key for Zitadel Actions V2 complementToken target.
# Set after running scripts/configure_actions_v2.py.
ZITADEL_ACTIONS_SIGNING_KEY = os.environ.get("ZITADEL_ACTIONS_SIGNING_KEY", "")
# Shared secret for encrypting the Zitadel session cookie between login-app and Django.
# Must be set to the same value in both services.
SESSION_ENCRYPTION_KEY = os.environ.get("SESSION_ENCRYPTION_KEY", "dev-insecure-change-me")
# URL Zitadel uses to reach the complement-token endpoint on Django.
# In Docker: http://django:8000/api/actions/complement-token
# In production: https://api.iam.clet.gov.gh/api/actions/complement-token
ACTIONS_TARGET_ENDPOINT = os.environ.get(
    "ACTIONS_TARGET_ENDPOINT",
    "http://django:8000/api/actions/complement-token",
)

BOOTSTRAP_ADMIN_EMAIL = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "admin@clet.gov.gh")
BOOTSTRAP_ZITADEL_ADMIN_EMAIL = os.environ.get("BOOTSTRAP_ZITADEL_ADMIN_EMAIL", "admin@zitadel.localhost")

AUDIT_RETENTION_YEARS = 10
AUDIT_OUTBOX_MAX_RETRIES = 5
AUDIT_CHAIN_ANCHOR_INTERVAL_HOURS = 24

SCIM_BEARER_TOKEN = os.environ.get("SCIM_BEARER_TOKEN", "")

SYSTEM_22_AUDIT_URL = os.environ.get("SYSTEM_22_AUDIT_URL", "")

OTEL_ENABLED = os.environ.get("OTEL_ENABLED", "false").lower() == "true"

PAM_RECORDING_RETENTION_YEARS = 7
PAM_VAULT_ADDR = os.environ.get("PAM_VAULT_ADDR", "")
PAM_VAULT_TOKEN = os.environ.get("PAM_VAULT_TOKEN", "")
PAM_JUMPSERVER_API_URL = os.environ.get("PAM_JUMPSERVER_API_URL", "")
PAM_JUMPSERVER_API_TOKEN = os.environ.get("PAM_JUMPSERVER_API_TOKEN", "")

# Per-user-type session & MFA policy profiles (IAM-F07/TYPE-5).
# Used by accounts/management/commands/configure_session_policies.py and
# referenced at runtime by the login flow to determine per-type MFA mandate.
USER_TYPE_POLICIES = {
    "default": {"force_mfa": True, "session_idle_lifetime": "864000s", "session_max_lifetime": "2592000s"},
    "public": {"force_mfa": False, "session_idle_lifetime": "3600s", "session_max_lifetime": "86400s"},
    "staff": {"force_mfa": True, "session_idle_lifetime": "28800s", "session_max_lifetime": "86400s"},
    "board": {"force_mfa": True, "session_idle_lifetime": "14400s", "session_max_lifetime": "43200s"},
    "nbec": {"force_mfa": True, "session_idle_lifetime": "14400s", "session_max_lifetime": "43200s"},
    "student": {"force_mfa": False, "session_idle_lifetime": "7200s", "session_max_lifetime": "86400s"},
    "external": {"force_mfa": False, "session_idle_lifetime": "3600s", "session_max_lifetime": "86400s"},
}
