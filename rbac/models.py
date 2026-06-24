import uuid

from django.db import models


class Role(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    system_code = models.CharField(max_length=100, db_index=True)
    role_id = models.CharField(max_length=100, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    permission_strings = models.JSONField(default=list, blank=True)
    # Admin-tier role for its system (e.g. ams.admin). IAM only records the tier;
    # what an admin can do is enforced by the downstream system.
    is_admin = models.BooleanField(default=False)
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


class AccessReviewCampaign(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        COMPLETED = "completed", "Completed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    period = models.CharField(max_length=20, db_index=True)  # e.g. "2026-Q2"
    scope = models.JSONField(default=dict, blank=True)  # {"system_code": "ams"} or {}
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True)
    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="created_reviews")
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="completed_reviews")
    signed_report_ref = models.CharField(max_length=128, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rbac_access_review_campaign"


class AccessReviewItem(models.Model):
    class Decision(models.TextChoices):
        PENDING = "pending", "Pending"
        KEEP = "keep", "Keep"
        REVOKE = "revoke", "Revoke"
        CHANGE_ROLE = "change_role", "Change role"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(AccessReviewCampaign, on_delete=models.CASCADE, related_name="items")
    binding = models.ForeignKey("rbac.RoleBinding", on_delete=models.SET_NULL, null=True, blank=True, related_name="review_items")
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="review_items")
    system_code = models.CharField(max_length=50)
    role_id = models.CharField(max_length=100)
    decision = models.CharField(max_length=20, choices=Decision.choices, default=Decision.PENDING, db_index=True)
    new_role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    reviewer = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_items")
    note = models.TextField(blank=True, default="")
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rbac_access_review_item"
        indexes = [models.Index(fields=["campaign", "decision"])]


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
