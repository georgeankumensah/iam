from django.urls import path

from . import views

urlpatterns = [
    path("", views.login_view, name="login"),
    path("loginname", views.login_view, name="loginname"),
    path("password", views.login_view, name="password"),
    path("mfa/<str:factor>/", views.mfa_view, name="mfa"),
    path("passkey", views.login_view, name="passkey"),
    path("u2f", views.login_view, name="u2f"),
    path("otp/<str:method>/", views.login_view, name="otp"),
    path("consent", views.consent_view, name="consent"),
    path("password-reset", views.password_reset_view, name="password_reset"),
    path("register", views.login_view, name="register"),
    path("accounts", views.login_view, name="accounts"),
    path("logout", views.login_view, name="logout"),
    path("signedin", views.login_view, name="signedin"),
    path("verify", views.login_view, name="verify"),
    path("authenticator/set", views.login_view, name="authenticator_set"),
    path("device", views.login_view, name="device"),
    path("idp", views.login_view, name="idp"),
    path("error", views.error_view, name="login_error"),
    path("callback", views.callback_view, name="login_callback"),
]
