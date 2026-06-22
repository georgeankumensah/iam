from django.contrib import admin

from .models import PamSession


@admin.register(PamSession)
class PamSessionAdmin(admin.ModelAdmin):
    list_display = ["user", "target_host", "status", "started_at", "ended_at"]
    list_filter = ["status"]
