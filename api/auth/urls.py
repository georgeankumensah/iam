from django.urls import path
from .views import (
    auth_status,
    create_auth_session,
    revoke_auth_session,
    sync_auth_state
)

urlpatterns = [
    path("status", auth_status, name="auth-status"),
    path("sessions", create_auth_session, name="create-auth-session"),
    path("sessions/revoke", revoke_auth_session, name="revoke-auth-session"),
    path("sync", sync_auth_state, name="sync-auth-state"),
]
