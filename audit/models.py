
from django.db import models


class AuditEvent(models.Model):
    id = models.BigAutoField(primary_key=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    actor_user_id = models.UUIDField(db_index=True)
    actor_email = models.EmailField(max_length=254, blank=True, default="")
    action = models.CharField(max_length=255, db_index=True)
    entity_type = models.CharField(max_length=100, blank=True, default="")
    entity_id = models.CharField(max_length=255, blank=True, default="")
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, default="")
    channel = models.CharField(max_length=50, blank=True, default="", db_index=True)
    client_id = models.CharField(max_length=255, blank=True, default="")
    correlation_id = models.CharField(max_length=255, blank=True, default="")
    result = models.CharField(max_length=50, blank=True, default="success")
    redacted_metadata = models.JSONField(default=dict, blank=True)
    hash_chain_ref = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_auditevent"
        indexes = [
            models.Index(fields=["actor_user_id", "timestamp"]),
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["channel", "timestamp"]),
            models.Index(fields=["action", "timestamp"]),
        ]
        ordering = ["-timestamp"]


class AuditChainAnchor(models.Model):
    id = models.BigAutoField(primary_key=True)
    event_id = models.BigIntegerField(unique=True)
    hash_chain_ref = models.CharField(max_length=64, db_index=True)
    previous_hash = models.CharField(max_length=64, blank=True, default="")
    anchored_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_chainanchor"


class AuditOutbox(models.Model):
    id = models.BigAutoField(primary_key=True)
    event = models.ForeignKey(AuditEvent, on_delete=models.CASCADE, related_name="outbox_entries")
    target_url = models.URLField(max_length=1024)
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=5)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default="")
    delivered = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_outbox"
        indexes = [
            models.Index(fields=["delivered", "next_retry_at"]),
        ]


class ActiveSession(models.Model):
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="active_sessions")
    session_id = models.CharField(max_length=255, blank=True, default="")
    jti = models.CharField(max_length=255, unique=True, db_index=True)
    kind = models.CharField(max_length=50, default="oidc")
    issued_at = models.DateTimeField()
    expires_at = models.DateTimeField(null=True, blank=True)
    scope = models.JSONField(default=list, blank=True)
    claims_hash = models.CharField(max_length=64, blank=True, default="")
    revoked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_activesession"
        indexes = [
            models.Index(fields=["user", "revoked"]),
            models.Index(fields=["jti"]),
        ]
