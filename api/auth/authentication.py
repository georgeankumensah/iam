from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import AuthSession


class AuthTokenAuthentication(BaseAuthentication):
    """
    Authentication using session ID from request headers
    """

    def authenticate(self, request):
        # Get session ID from headers
        session_id = request.META.get('HTTP_X_SESSION_ID') or request.headers.get('X-Session-ID')

        if not session_id:
            return None

        try:
            # Validate session
            auth_session = AuthSession.objects.select_related('user').get(
                session_id=session_id,
                is_revoked=False
            )

            # Check if session is expired
            if auth_session.expires_at < timezone.now():
                auth_session.is_revoked = True
                auth_session.revoked_at = timezone.now()
                auth_session.save()
                raise AuthenticationFailed('Session expired')

            return (auth_session.user, auth_session)
        except AuthSession.DoesNotExist:
            raise AuthenticationFailed('Invalid session')
