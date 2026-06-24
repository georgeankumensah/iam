from django.urls import path
from .views import (
    auth_status,
    create_auth_session,
    revoke_auth_session,
    sync_auth_state
)

urlpatterns = [
    path("api/auth/status", auth_status, name="auth-status"),
    path("api/auth/sessions", create_auth_session, name="create-auth-session"),
    path("api/auth/sessions/revoke", revoke_auth_session, name="revoke-auth-session"),
    path("api/auth/sync", sync_auth_state, name="sync-auth-state"),
]
