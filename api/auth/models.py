from django.db import models
from django.utils import timezone
from uuid import uuid4
from django.contrib.auth import get_user_model

User = get_user_model()

class AuthSession(models.Model):
    """Centralized authentication session management"""
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='auth_sessions')
    session_id = models.CharField(max_length=255, unique=True, db_index=True)
    jti = models.CharField(max_length=255, unique=True, db_index=True)
    app_id = models.CharField(max_length=100, db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    last_activity = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.TextField(null=True)
    is_revoked = models.BooleanField(default=False)
    revoked_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'app_id', 'is_revoked']),
            models.Index(fields=['expires_at']),
        ]

class AuthState(models.Model):
    """Centralized authentication state synchronization"""
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='auth_states')
    app_id = models.CharField(max_length=100, db_index=True)
    session_id = models.CharField(max_length=255, db_index=True)
    authenticated = models.BooleanField(default=False)
    permissions = models.JSONField(default=list)
    roles = models.JSONField(default=list)
    expires_at = models.DateTimeField(db_index=True)
    last_sync = models.DateTimeField(auto_now=True)
    state_data = models.JSONField(default=dict)
    
    class Meta:
        unique_together = [['user', 'app_id']]
        indexes = [
            models.Index(fields=['user', 'app_id', 'authenticated']),
            models.Index(fields=['expires_at']),
        ]

class AuthEvent(models.Model):
    """Event logging for authentication state changes"""
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    event_type = models.CharField(max_length=50, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='auth_events')
    session_id = models.CharField(max_length=255, db_index=True)
    app_id = models.CharField(max_length=100, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    metadata = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.TextField(null=True)
