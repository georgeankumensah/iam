from django.contrib import admin

from .models import DPIA, DataResidency


@admin.register(DataResidency)
class DataResidencyAdmin(admin.ModelAdmin):
    list_display = (
        "service_name", "region", "data_classification", "is_backup", "last_reviewed_at",
    )
    list_filter = ("region", "is_backup")
    search_fields = ("service_name",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(DPIA)
class DPIAAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "signed_at", "review_date")
    list_filter = ("status",)
    search_fields = ("title",)
    readonly_fields = ("id", "created_at", "updated_at")
