from django.urls import path

from . import views

urlpatterns = [
    path("", views.login_view, name="login"),
    path("mfa/<str:factor>/", views.mfa_view, name="mfa"),
    path("consent", views.consent_view, name="consent"),
    path("password-reset", views.password_reset_view, name="password_reset"),
    path("error", views.error_view, name="login_error"),
    path("callback", views.callback_view, name="login_callback"),
]
