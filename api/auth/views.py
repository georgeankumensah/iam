from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .authentication import AuthTokenAuthentication
from .services import AuthService, AuthStateSyncService


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([AuthTokenAuthentication])
def auth_status(request):
    """Get authentication status for the current user"""
    try:
        # Get user from request
        user = request.user

        # Get all app states
        app_states = AuthStateSyncService.get_all_app_states(user)

        # Build response
        auth_data = []
        for state in app_states:
            auth_data.append({
                'app_id': state.app_id,
                'session_id': state.session_id,
                'authenticated': state.authenticated,
                'expires_at': state.expires_at.isoformat(),
                'last_sync': state.last_sync.isoformat(),
                'permissions': state.permissions,
                'roles': state.roles
            })

        return Response({
            'success': True,
            'data': {
                'user_id': str(user.id),
                'email': user.email,
                'app_states': auth_data
            }
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': 'AUTH_STATUS_ERROR',
            'error_description': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([AuthTokenAuthentication])
def create_auth_session(request):
    """Create a new authentication session"""
    try:
        data = request.data
        user = request.user

        # Validate required fields
        required_fields = ['session_id', 'jti', 'app_id', 'expires_at']
        for field in required_fields:
            if field not in data:
                return Response({
                    'success': False,
                    'error': 'VALIDATION_ERROR',
                    'error_description': f'Missing required field: {field}'
                }, status=status.HTTP_400_BAD_REQUEST)

        # Parse expires_at
        from django.utils.dateparse import parse_datetime
        expires_at = parse_datetime(data['expires_at'])
        if not expires_at:
            return Response({
                'success': False,
                'error': 'VALIDATION_ERROR',
                'error_description': 'Invalid expires_at format'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create session
        session = AuthService.create_session(
            user=user,
            session_id=data['session_id'],
            jti=data['jti'],
            app_id=data['app_id'],
            expires_at=expires_at,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )

        return Response({
            'success': True,
            'data': {
                'session_id': session.session_id,
                'expires_at': session.expires_at.isoformat(),
                'app_id': session.app_id
            }
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': 'CREATE_SESSION_ERROR',
            'error_description': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([AuthTokenAuthentication])
def revoke_auth_session(request):
    """Revoke an authentication session"""
    try:
        data = request.data
        user = request.user

        # Validate required fields
        if 'session_id' not in data:
            return Response({
                'success': False,
                'error': 'VALIDATION_ERROR',
                'error_description': 'Missing required field: session_id'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Revoke session
        AuthService.revoke_session(data['session_id'], user.id)

        return Response({
            'success': True,
            'data': {
                'session_id': data['session_id'],
                'revoked': True
            }
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': 'REVOKE_SESSION_ERROR',
            'error_description': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([AuthTokenAuthentication])
def sync_auth_state(request):
    """Synchronize authentication state for an app"""
    try:
        data = request.data
        user = request.user

        # Validate required fields
        required_fields = ['app_id', 'session_id', 'authenticated']
        for field in required_fields:
            if field not in data:
                return Response({
                    'success': False,
                    'error': 'VALIDATION_ERROR',
                    'error_description': f'Missing required field: {field}'
                }, status=status.HTTP_400_BAD_REQUEST)

        # Parse optional fields
        from django.utils.dateparse import parse_datetime
        expires_at = parse_datetime(data.get('expires_at')) if data.get('expires_at') else None

        # Sync state
        state = AuthStateSyncService.sync_auth_state(
            user=user,
            app_id=data['app_id'],
            session_data={
                'session_id': data['session_id'],
                'authenticated': data['authenticated'],
                'permissions': data.get('permissions', []),
                'roles': data.get('roles', []),
                'expires_at': expires_at,
                'state_data': data.get('state_data', {})
            }
        )

        return Response({
            'success': True,
            'data': {
                'state_id': str(state.id),
                'app_id': state.app_id,
                'session_id': state.session_id,
                'authenticated': state.authenticated,
                'last_sync': state.last_sync.isoformat()
            }
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': 'SYNC_AUTH_STATE_ERROR',
            'error_description': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
