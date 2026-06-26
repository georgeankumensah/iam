import uuid

from django.conf import settings
from django.db import models


class HrmsEvent(models.Model):
    """Persisted record of every signature-verified HRMS SCIM/webhook event.

    Enables the admin surface (IAM-F06): list events, replay failures, and
    resolve move-conflicts (events that could not be applied cleanly).
    """

    class EventType(models.TextChoices):
        JOINER = "hrms.joiner", "Joiner"
        MOVER = "hrms.mover", "Mover"
        LEAVER = "hrms.leaver", "Leaver"

    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"
        CONFLICT = "conflict", "Conflict"
        RESOLVED = "resolved", "Resolved"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=32, choices=EventType.choices, db_index=True)
    target_email = models.EmailField(blank=True, db_index=True)
    payload = models.JSONField(default=dict)
    signature_valid = models.BooleanField(default=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RECEIVED, db_index=True)
    result = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    replay_count = models.PositiveIntegerField(default=0)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="resolved_hrms_events"
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True)

    class Meta:
        ordering = ["-received_at"]
        indexes = [models.Index(fields=["status", "event_type"])]

    def __str__(self) -> str:
        return f"{self.event_type} {self.target_email} ({self.status})"
