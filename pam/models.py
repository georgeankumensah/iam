import uuid

from django.db import models


class PamSession(models.Model):
    class SessionStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        ENDED = "ended", "Ended"
        REVOKED = "revoked", "Revoked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="pam_sessions")
    target_id = models.CharField(max_length=255, blank=True, default="")
    target_host = models.CharField(max_length=255, blank=True, default="")
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    recording_uri = models.URLField(max_length=1024, blank=True, default="")
    recording_sha256 = models.CharField(max_length=64, blank=True, default="")
    vault_lease_id = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=20, choices=SessionStatus.choices, default=SessionStatus.ACTIVE, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pam_pamsession"
        indexes = [
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self) -> str:
        return f"PAM:{self.user} @ {self.target_host}"
