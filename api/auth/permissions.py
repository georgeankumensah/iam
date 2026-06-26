from django.utils import timezone
from rest_framework import permissions

from .models import AuthSession


class HasValidSessionPermission(permissions.BasePermission):
    """
    Permission check for valid authentication session
    """

    def has_permission(self, request, view):
        session_id = request.META.get('HTTP_X_SESSION_ID') or request.headers.get('X-Session-ID')

        if not session_id:
            return False

        try:
            auth_session = AuthSession.objects.get(
                session_id=session_id,
                is_revoked=False
            )

            # Check if session is expired
            if auth_session.expires_at < timezone.now():
                return False

            return True
        except AuthSession.DoesNotExist:
            return False

class HasAppPermission(permissions.BasePermission):
    """
    Permission check for specific app access
    """

    def has_permission(self, request, view):
        session_id = request.META.get('HTTP_X_SESSION_ID') or request.headers.get('X-Session-ID')
        app_id = request.headers.get('X-App-ID')

        if not session_id or not app_id:
            return False

        try:
            auth_session = AuthSession.objects.get(
                session_id=session_id,
                app_id=app_id,
                is_revoked=False
            )

            # Check if session is expired
            if auth_session.expires_at < timezone.now():
                return False

            return True
        except AuthSession.DoesNotExist:
            return False
