from django.contrib import admin
from django.urls import include, path

from oidc_rp.views import me_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", include("login.urls")),
    path("oidc/", include("oidc_rp.urls")),
    path("backchannel-logout", include("oidc_rp.urls")),
    path("scim/v2/", include("lifecycle.urls")),
    path("v1/admin/", include("console.urls")),
    path("v1/me", me_view, name="self_service"),
    path("delegation/", include("delegation.urls")),
    path("pam/", include("pam.urls")),
    path("health/", include("core.health_urls")),
]
