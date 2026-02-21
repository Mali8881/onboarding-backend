from django.contrib import admin

from .models import Regulation, RegulationAcknowledgement


@admin.register(Regulation)
class RegulationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "type",
        "language",
        "is_active",
        "is_mandatory_on_day_one",
        "position",
        "created_at",
        "updated_at",
    )
    list_filter = (
        "type",
        "language",
        "is_active",
        "is_mandatory_on_day_one",
    )
    search_fields = ("title", "description")
    ordering = ("position",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(RegulationAcknowledgement)
class RegulationAcknowledgementAdmin(admin.ModelAdmin):
    list_display = (
        "acknowledged_at",
        "user",
        "user_full_name",
        "regulation",
        "regulation_title",
    )
    list_filter = ("acknowledged_at",)
    search_fields = ("user__username", "user_full_name", "regulation__title", "regulation_title")
    readonly_fields = (
        "user",
        "regulation",
        "acknowledged_at",
        "user_full_name",
        "regulation_title",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
