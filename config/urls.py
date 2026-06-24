from django.contrib import admin
from django.urls import include, path

from console.views.invitations import invitation_accept
from oidc_rp.views import me_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("v1/onboarding/accept", invitation_accept, name="onboarding_accept"),
    path("login/", include("login.urls")),
    path("oidc/", include("oidc_rp.urls")),
    path("backchannel-logout", include("oidc_rp.urls")),
    path("scim/v2/", include("lifecycle.urls")),
    path("v1/admin/", include("console.urls")),
    path("v1/me", me_view, name="self_service"),
    path("delegation/", include("delegation.urls")),
    path("pam/", include("pam.urls")),
    path("health/", include("core.health_urls")),
    path("api/auth/", include("api.auth.urls")),
]
