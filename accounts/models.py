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
    zitadel_user_id = models.UUIDField(unique=True, null=True, blank=True, db_index=True)
    email = models.EmailField(unique=True, db_index=True)
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
