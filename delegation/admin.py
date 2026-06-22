from django.contrib import admin

from .models import Delegation, DelegationWebhookEvent


@admin.register(Delegation)
class DelegationAdmin(admin.ModelAdmin):
    list_display = ["delegator", "delegate", "role", "state", "start_at", "end_at"]
    list_filter = ["state"]


@admin.register(DelegationWebhookEvent)
class DelegationWebhookEventAdmin(admin.ModelAdmin):
    list_display = ["event_type", "processed", "created_at"]
