import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from .managers import UserManager


class UserType(models.TextChoices):
    STAFF = "staff", "Staff"
    BOARD = "board", "Board Member"
    NBEC = "nbec", "NBEC"
    STUDENT = "student", "Student"
    EXTERNAL = "external", "External"
    PUBLIC = "public", "Public"


class UserStatus(models.TextChoices):
    PRE_ACTIVE = "pre_active", "Pre-Active"
    ACTIVE = "active", "Active"
    DISABLED = "disabled", "Disabled"
    PENDING = "pending", "Pending"


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    zitadel_user_id = models.CharField(max_length=255, unique=True, null=True, blank=True, db_index=True)
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=150, blank=True, default="")
    last_name = models.CharField(max_length=150, blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")
    user_type = models.CharField(max_length=20, choices=UserType.choices, default=UserType.EXTERNAL, db_index=True)
    status = models.CharField(max_length=20, choices=UserStatus.choices, default=UserStatus.PRE_ACTIVE, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    hrms_event_ref = models.CharField(max_length=255, blank=True, default="")
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        db_table = "accounts_user"
        indexes = [
            models.Index(fields=["user_type", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.email} ({self.user_type})"

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE


class ZitadelUserSync(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="zitadel_sync")
    zitadel_resource_id = models.CharField(max_length=255, blank=True, default="")
    last_sync_at = models.DateTimeField(null=True, blank=True)
    sync_status = models.CharField(max_length=50, default="pending")
    error_log = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "accounts_zitadel_sync"


class Invitation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REVOKED = "revoked", "Revoked"
        EXPIRED = "expired", "Expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(db_index=True)
    system_code = models.CharField(max_length=50, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="invitations", null=True, blank=True)
    zitadel_user_id = models.CharField(max_length=255, blank=True, default="", db_index=True)
    role_ids = models.JSONField(default=list, blank=True)
    as_admin = models.BooleanField(default=False)
    token_hash = models.CharField(max_length=64, blank=True, default="", db_index=True)
    lookup_token_hash = models.CharField(max_length=64, blank=True, default="", db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    invited_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="sent_invitations"
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_invitation"
        indexes = [
            models.Index(fields=["email", "status"]),
            models.Index(fields=["system_code", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.email} → {self.system_code} ({self.status})"


class RecoveryCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recovery_codes")
    code_hash = models.CharField(max_length=64, db_index=True)
    masked_code = models.CharField(max_length=20)
    used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_recoverycode"
        indexes = [models.Index(fields=["user", "used"])]
