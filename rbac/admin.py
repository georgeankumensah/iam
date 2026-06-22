from django.contrib import admin

from .models import Role, RoleBinding, RuleDefinition


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["system_code", "role_id", "name", "version", "is_deprecated"]
    list_filter = ["system_code", "is_deprecated"]
    search_fields = ["system_code", "role_id", "name"]


@admin.register(RoleBinding)
class RoleBindingAdmin(admin.ModelAdmin):
    list_display = ["role", "user", "state", "effective_from", "effective_to"]
    list_filter = ["state"]


@admin.register(RuleDefinition)
class RuleDefinitionAdmin(admin.ModelAdmin):
    list_display = ["name", "severity", "enabled", "version"]
