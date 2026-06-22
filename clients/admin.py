from django.contrib import admin

from .models import OIDCClient


@admin.register(OIDCClient)
class OIDCClientAdmin(admin.ModelAdmin):
    list_display = ["client_id", "lifecycle_state", "compliance_gate_passed", "created_at"]
    list_filter = ["lifecycle_state", "compliance_gate_passed"]
    search_fields = ["client_id", "client_id_hash"]
