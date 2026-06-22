from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "user_type", "status", "created_at", "last_login_at"]
    list_filter = ["user_type", "status"]
    search_fields = ["email", "zitadel_user_id"]
    ordering = ["-created_at"]
    fieldsets = [
        (None, {"fields": ["email", "phone", "user_type", "status"]}),
        ("Identity", {"fields": ["zitadel_user_id", "metadata", "hrms_event_ref"]}),
        ("Permissions", {"fields": ["is_staff", "is_superuser", "groups", "user_permissions"]}),
        ("Timestamps", {"fields": ["last_login_at", "created_at", "updated_at"]}),
    ]
    readonly_fields = ["created_at", "updated_at"]
    add_fieldsets = [
        (None, {"classes": ["wide"], "fields": ["email", "user_type", "status"]}),
    ]
