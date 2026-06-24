# Auth service package for IAM Django API
# Provides centralized authentication state management

__version__ = '1.0.0'
__author__ = 'IAM Team'

__all__ = [
    'AuthService',
    'AuthStateSyncService',
    'AuthSession',
    'AuthState',
    'AuthEvent',
    'auth_status',
    'create_auth_session',
    'revoke_auth_session',
    'sync_auth_state',
    'AuthTokenAuthentication',
    'HasValidSessionPermission',
    'HasAppPermission',
    'AuthSessionSerializer',
    'AuthStateSerializer',
    'AuthEventSerializer',
    'CreateAuthSessionSerializer',
    'SyncAuthStateSerializer',
]
