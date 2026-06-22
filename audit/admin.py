from django.contrib import admin

from .models import AuditChainAnchor, AuditEvent, AuditOutbox


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ["id", "timestamp", "action", "actor_email", "result", "channel"]
    list_filter = ["action", "channel", "result"]
    search_fields = ["actor_email", "entity_id", "correlation_id"]
    readonly_fields = ["id", "timestamp", "hash_chain_ref"]


@admin.register(AuditChainAnchor)
class AuditChainAnchorAdmin(admin.ModelAdmin):
    list_display = ["event_id", "anchored_at", "hash_chain_ref"]


@admin.register(AuditOutbox)
class AuditOutboxAdmin(admin.ModelAdmin):
    list_display = ["id", "delivered", "retry_count", "next_retry_at"]
