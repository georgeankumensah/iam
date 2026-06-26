from django.contrib import admin

from .models import HrmsEvent


@admin.register(HrmsEvent)
class HrmsEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "target_email", "status", "signature_valid", "received_at", "processed_at")
    list_filter = ("event_type", "status", "signature_valid")
    search_fields = ("target_email",)
    readonly_fields = ("id", "received_at", "processed_at", "replay_count", "resolved_at")
    ordering = ("-received_at",)
