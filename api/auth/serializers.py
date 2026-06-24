from rest_framework import serializers
from .models import AuthSession, AuthState, AuthEvent

class AuthSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthSession
        fields = [
            'id', 'user', 'session_id', 'jti', 'app_id', 
            'expires_at', 'last_activity', 'ip_address', 
            'user_agent', 'is_revoked', 'revoked_at', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class AuthStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthState
        fields = [
            'id', 'user', 'app_id', 'session_id', 'authenticated',
            'permissions', 'roles', 'expires_at', 'last_sync', 'state_data'
        ]
        read_only_fields = ['id', 'last_sync']

class AuthEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthEvent
        fields = [
            'id', 'event_type', 'user', 'session_id', 'app_id',
            'timestamp', 'metadata', 'ip_address', 'user_agent'
        ]
        read_only_fields = ['id', 'timestamp']

class CreateAuthSessionSerializer(serializers.Serializer):
    session_id = serializers.CharField()
    jti = serializers.CharField()
    app_id = serializers.CharField()
    expires_at = serializers.DateTimeField()
    ip_address = serializers.IPAddressField(required=False, allow_null=True)
    user_agent = serializers.CharField(required=False, allow_null=True)

class SyncAuthStateSerializer(serializers.Serializer):
    app_id = serializers.CharField()
    session_id = serializers.CharField()
    authenticated = serializers.BooleanField()
    permissions = serializers.ListField(required=False, default=list)
    roles = serializers.ListField(required=False, default=list)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    state_data = serializers.DictField(required=False, default=dict)
