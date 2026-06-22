from django.urls import path

from . import backchannel, views

urlpatterns = [
    path("logout", views.logout_view, name="oidc_logout"),
    path("backchannel-logout", backchannel.backchannel_logout, name="backchannel_logout"),
]
