import uuid

from django.conf import settings
from django.db import models


class DataResidency(models.Model):
    """Track data residency location for each service in the IAM platform.

    Required by SRS-IAM-N10: document residency for all services (incl. Zitadel
    DB region, PostgreSQL, Redis, backups) with annual review stamps.
    """

    class Region(models.TextChoices):
        GHANA = "ghana", "Ghana (Accra DC)"
        EU_WEST_2 = "eu-west-2", "UK / London"
        EU_WEST_1 = "eu-west-1", "Ireland"
        US_EAST_1 = "us-east-1", "US East (N. Virginia)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_name = models.CharField(max_length=128, unique=True, db_index=True)
    description = models.TextField(blank=True)
    region = models.CharField(max_length=32, choices=Region.choices, default=Region.GHANA)
    data_classification = models.CharField(max_length=64, default="confidential")
    is_backup = models.BooleanField(default=False)
    backup_region = models.CharField(max_length=32, choices=Region.choices, blank=True, default="")
    notes = models.TextField(blank=True)
    last_reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="residency_reviews",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Data residencies"
        ordering = ["service_name"]

    def __str__(self) -> str:
        return f"{self.service_name} ({self.region})"


class DPIA(models.Model):
    """Data Protection Impact Assessment sign-off record.

    Required by SRS-IAM-N11 (Act 843, Ghana): capture sign-off, reviewer,
    document reference, and annual review schedule.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    document_ref = models.CharField(
        max_length=128, blank=True, help_text="Document ID or file reference",
    )
    description = models.TextField(blank=True)
    signed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="dpia_signoffs",
    )
    signed_at = models.DateTimeField(null=True, blank=True)
    review_date = models.DateTimeField(null=True, blank=True, help_text="Next annual review due")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="dpia_reviews",
    )
    status = models.CharField(
        max_length=32,
        choices=[
            ("draft", "Draft"),
            ("signed", "Signed"),
            ("reviewed", "Reviewed"),
            ("superseded", "Superseded"),
        ],
        default="draft",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "DPIA"
        ordering = ["-signed_at"]

    def __str__(self) -> str:
        return f"{self.title} ({self.status})"
