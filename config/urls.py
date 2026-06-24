from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from console.views.invitations import invitation_accept
from oidc_rp.views import me_view, my_apps, my_sessions, terminate_my_session

urlpatterns = [
    path("admin/", admin.site.urls),
    # OpenAPI schema + interactive docs
    path("api/schema", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("v1/onboarding/accept", invitation_accept, name="onboarding_accept"),
    path("v1/", include("console.onboarding_urls")),
    path("login/", include("login.urls")),
    path("oidc/", include("oidc_rp.urls")),
    path("backchannel-logout", include("oidc_rp.urls")),
    path("scim/v2/", include("lifecycle.urls")),
    path("v1/admin/", include("console.urls")),
    path("v1/me", me_view, name="self_service"),
    path("v1/me/apps", my_apps, name="my_apps"),
    path("v1/me/sessions", my_sessions, name="my_sessions"),
    path("v1/me/sessions/<str:session_id>", terminate_my_session, name="terminate_my_session"),
    path("delegation/", include("delegation.urls")),
    path("pam/", include("pam.urls")),
    path("health/", include("core.health_urls")),
    path("api/auth/", include("api.auth.urls")),
]
