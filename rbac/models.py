import uuid

from django.db import models


class Role(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    system_code = models.CharField(max_length=100, db_index=True)
    role_id = models.CharField(max_length=100, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    permission_strings = models.JSONField(default=list, blank=True)
    version = models.IntegerField(default=1)
    owner_system = models.CharField(max_length=100, blank=True, default="")
    effective_from = models.DateTimeField(null=True, blank=True)
    is_deprecated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rbac_role"
        unique_together = [["system_code", "role_id", "version"]]
        indexes = [
            models.Index(fields=["system_code", "is_deprecated"]),
        ]

    def __str__(self) -> str:
        return f"{self.system_code}:{self.role_id} v{self.version}"


class RoleBinding(models.Model):
    class BindingState(models.TextChoices):
        REQUESTED = "requested", "Requested"
        APPROVED = "approved", "Approved"
        EFFECTIVE = "effective", "Effective"
        REVOKED = "revoked", "Revoked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="bindings")
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="role_bindings")
    state = models.CharField(max_length=20, choices=BindingState.choices, default=BindingState.REQUESTED, db_index=True)
    approver = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_bindings"
    )
    effective_from = models.DateTimeField(null=True, blank=True)
    effective_to = models.DateTimeField(null=True, blank=True)
    justification = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rbac_rolebinding"
        indexes = [
            models.Index(fields=["user", "state"]),
            models.Index(fields=["role", "state"]),
        ]


class RoleClaim(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="claims")
    zitadel_claim_key = models.CharField(max_length=255)
    zitadel_claim_value = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rbac_roleclaim"
        unique_together = [["role", "zitadel_claim_key"]]


class RuleDefinition(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    severity = models.CharField(max_length=50, default="medium")
    predicate_json = models.JSONField(default=dict)
    version = models.IntegerField(default=1)
    enabled = models.BooleanField(default=True)
    approved_by = models.CharField(max_length=255, blank=True, default="")
    effective_from = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rbac_ruledefinition"
