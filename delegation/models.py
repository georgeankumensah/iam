import uuid

from django.db import models


class Delegation(models.Model):
    class DelegationState(models.TextChoices):
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        REVOKED = "revoked", "Revoked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    delegator = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="delegations_given")
    delegate = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="delegations_received")
    role = models.ForeignKey("rbac.Role", on_delete=models.CASCADE, related_name="delegations")
    justification = models.TextField(blank=True, default="")
    start_at = models.DateTimeField()
    end_at = models.DateTimeField(db_index=True)
    state = models.CharField(max_length=20, choices=DelegationState.choices, default=DelegationState.ACTIVE, db_index=True)
    source_event_id = models.CharField(max_length=255, blank=True, default="")
    source_system = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "delegation_delegation"
        indexes = [
            models.Index(fields=["state", "end_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.delegator} → {self.delegate} ({self.role})"


class DelegationWebhookEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    signature = models.CharField(max_length=255)
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    error_log = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "delegation_webhookevent"
        ordering = ["-created_at"]
