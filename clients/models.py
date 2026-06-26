import hashlib
import uuid

from django.db import models


class ClientLifecycleState(models.TextChoices):
    ONBOARDING = "onboarding", "Onboarding"
    SANDBOX_VALIDATED = "sandbox_validated", "Sandbox Validated"
    PRODUCTION_LIVE = "production_live", "Production Live"
    SUSPENDED = "suspended", "Suspended"
    DECOMMISSIONED = "decommissioned", "Decommissioned"


class OIDCClient(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Short, stable code for the downstream system (e.g. "ams", "nbes"); ties the
    # client to its rbac.Role catalogue (Role.system_code) and onboarding routes.
    system_code = models.CharField(max_length=50, blank=True, default="", db_index=True)
    name = models.CharField(max_length=255, blank=True, default="")
    zitadel_project_id = models.CharField(max_length=255, blank=True, default="")
    zitadel_app_id = models.CharField(max_length=255, blank=True, default="")
    client_id = models.CharField(max_length=255, unique=True, db_index=True)
    client_id_hash = models.CharField(max_length=64, blank=True, default="")
    lifecycle_state = models.CharField(
        max_length=30,
        choices=ClientLifecycleState.choices,
        default=ClientLifecycleState.ONBOARDING,
    )
    owner_id = models.UUIDField(blank=True, null=True)
    redirect_uris = models.JSONField(default=list, blank=True)
    post_logout_redirect_uris = models.JSONField(default=list, blank=True)
    scopes = models.JSONField(default=list, blank=True)
    secret_rotated_at = models.DateTimeField(null=True, blank=True)
    compliance_gate_passed = models.BooleanField(default=False)
    granted_system_refs = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    # Per-client claim allow-list.  If non-empty, only these claim keys from
    # the complement-token target are injected into the token for this client.
    # Keys: "user_type", "portal_access", "permissions".
    claim_allow_list = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "clients_oidcclient"
        indexes = [
            models.Index(fields=["lifecycle_state"]),
        ]

    def __str__(self) -> str:
        return f"{self.client_id} ({self.lifecycle_state})"

    def save(self, *args, **kwargs):
        if self.client_id and not self.client_id_hash:
            self.client_id_hash = hashlib.sha256(self.client_id.encode()).hexdigest()
        super().save(*args, **kwargs)
