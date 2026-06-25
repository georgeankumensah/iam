import os
from pathlib import Path

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
        "schedule": 3600.0,  # hourly
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
OIDC_OP_JWKS_ENDPOINT = f"{os.environ.get('ZITADEL_HOST', '')}/oauth/v2/keys"
OIDC_OP_AUTHORIZATION_ENDPOINT = f"{os.environ.get('ZITADEL_HOST', '')}/oauth/v2/authorize"
OIDC_OP_TOKEN_ENDPOINT = f"{os.environ.get('ZITADEL_HOST', '')}/oauth/v2/token"
OIDC_OP_USERINFO_ENDPOINT = f"{os.environ.get('ZITADEL_HOST', '')}/oauth/v2/userinfo"
OIDC_OP_LOGOUT_ENDPOINT = f"{os.environ.get('ZITADEL_HOST', '')}/oauth/v2/end_session"
OIDC_RP_SIGN_ALGO = "RS256"
OIDC_RP_SCOPES = "openid email profile"
OIDC_RP_IDP_SIGN_KEY = None
OIDC_CREATE_USER = True
OIDC_STORE_ACCESS_TOKEN = True
OIDC_STORE_ID_TOKEN = True
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX_ATTEMPTS = 20
RATE_LIMIT_PATHS = ["/login/", "/password-reset/"]

BOOTSTRAP_ADMIN_EMAIL = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "admin@clet.gov.gh")
BOOTSTRAP_ZITADEL_ADMIN_EMAIL = os.environ.get("BOOTSTRAP_ZITADEL_ADMIN_EMAIL", "admin@zitadel.localhost")

AUDIT_RETENTION_YEARS = 10
AUDIT_OUTBOX_MAX_RETRIES = 5
AUDIT_CHAIN_ANCHOR_INTERVAL_HOURS = 24

SCIM_BEARER_TOKEN = os.environ.get("SCIM_BEARER_TOKEN", "")

SYSTEM_22_AUDIT_URL = os.environ.get("SYSTEM_22_AUDIT_URL", "")

PAM_RECORDING_RETENTION_YEARS = 7
PAM_VAULT_ADDR = os.environ.get("PAM_VAULT_ADDR", "")
PAM_VAULT_TOKEN = os.environ.get("PAM_VAULT_TOKEN", "")
