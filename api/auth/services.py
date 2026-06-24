from django.utils import timezone
from django.db import transaction
from .models import AuthSession, AuthState, AuthEvent

class AuthService:
    """Core authentication service with session management"""
    
    @staticmethod
    def create_session(user, session_id, jti, app_id, expires_at, ip_address=None, user_agent=None):
        """Create a new authentication session"""
        with transaction.atomic():
            # Create auth session
            auth_session = AuthSession.objects.create(
                user=user,
                session_id=session_id,
                jti=jti,
                app_id=app_id,
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Create auth state
            AuthState.objects.update_or_create(
                user=user,
                app_id=app_id,
                defaults={
                    'session_id': session_id,
                    'authenticated': True,
                    'expires_at': expires_at,
                    'permissions': [],
                    'roles': [],
                }
            )
            
            # Log event
            AuthEvent.objects.create(
                event_type='LOGIN',
                user=user,
                session_id=session_id,
                app_id=app_id,
                metadata={'ip_address': ip_address, 'user_agent': user_agent}
            )
            
            return auth_session
    
    @staticmethod
    def validate_session(session_id, app_id=None):
        """Validate an authentication session"""
        try:
            auth_session = AuthSession.objects.select_related('user').get(
                session_id=session_id,
                is_revoked=False
            )
            
            # Check if session is expired
            if auth_session.expires_at < timezone.now():
                AuthService.revoke_session(auth_session.id, auth_session.user.id)
                return None, 'Session expired'
            
            # Check if session belongs to specific app (if provided)
            if app_id and auth_session.app_id != app_id:
                return None, 'Session does not belong to this app'
            
            return auth_session, None
        except AuthSession.DoesNotExist:
            return None, 'Session not found or revoked'
    
    @staticmethod
    def revoke_session(session_id, user_id):
        """Revoke an authentication session"""
        with transaction.atomic():
            auth_session = AuthSession.objects.get(id=session_id, user_id=user_id)
            auth_session.is_revoked = True
            auth_session.revoked_at = timezone.now()
            auth_session.save()
            
            # Update auth state
            AuthState.objects.filter(user_id=user_id, session_id=session_id).update(
                authenticated=False
            )
            
            # Log event
            AuthEvent.objects.create(
                event_type='LOGOUT',
                user_id=user_id,
                session_id=session_id,
                app_id=auth_session.app_id,
                metadata={'reason': 'session_revoked'}
            )
    
    @staticmethod
    def refresh_session(session_id, user_id, new_expires_at):
        """Refresh an authentication session"""
        auth_session = AuthSession.objects.get(id=session_id, user_id=user_id)
        auth_session.expires_at = new_expires_at
        auth_session.last_activity = timezone.now()
        auth_session.save()
        
        # Update auth state
        AuthState.objects.filter(user_id=user_id, session_id=session_id).update(
            expires_at=new_expires_at
        )
        
        # Log event
        AuthEvent.objects.create(
            event_type='SESSION_REFRESH',
            user_id=user_id,
            session_id=session_id,
            app_id=auth_session.app_id,
            metadata={'new_expires_at': new_expires_at.isoformat()}
        )
    
    @staticmethod
    def get_auth_state(user, app_id):
        """Get authentication state for a user and app"""
        try:
            auth_state = AuthState.objects.get(user=user, app_id=app_id)
            return auth_state
        except AuthState.DoesNotExist:
            return None

class AuthStateSyncService:
    """Service for synchronizing authentication state between apps"""
    
    @staticmethod
    def sync_auth_state(user, app_id, session_data):
        """Synchronize authentication state for an app"""
        auth_state, created = AuthState.objects.update_or_create(
            user=user,
            app_id=app_id,
            defaults={
                'session_id': session_data.get('session_id'),
                'authenticated': session_data.get('authenticated', False),
                'permissions': session_data.get('permissions', []),
                'roles': session_data.get('roles', []),
                'expires_at': session_data.get('expires_at'),
                'state_data': session_data.get('state_data', {})
            }
        )
        
        # Log state change event
        AuthEvent.objects.create(
            event_type='STATE_SYNC',
            user=user,
            session_id=session_data.get('session_id'),
            app_id=app_id,
            metadata=session_data
        )
        
        return auth_state
    
    @staticmethod
    def get_all_app_states(user):
        """Get authentication states for all apps for a user"""
        return AuthState.objects.filter(user=user, authenticated=True)
    
    @staticmethod
    def cleanup_expired_states():
        """Clean up expired authentication states"""
        expired_states = AuthState.objects.filter(
            expires_at__lt=timezone.now(),
            authenticated=True
        )
        
        for state in expired_states:
            state.authenticated = False
            state.save()
            
            # Log expiration event
            AuthEvent.objects.create(
                event_type='SESSION_EXPIRED',
                user=state.user,
                session_id=state.session_id,
                app_id=state.app_id,
                metadata={'expired_at': timezone.now().isoformat()}
            )
