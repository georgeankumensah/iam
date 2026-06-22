from django.urls import path

from . import health_views

urlpatterns = [
    path("live", health_views.liveness, name="health_live"),
    path("ready", health_views.readiness, name="health_ready"),
]
