from django.contrib import admin
from accounts.access_policy import AccessPolicy

from .models import Regulation, RegulationAcknowledgement


@admin.register(Regulation)
class RegulationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "type",
        "is_active",
        "is_mandatory_on_day_one",
        "position",
        "created_at",
        "updated_at",
    )
    list_filter = (
        "type",
        "is_active",
        "is_mandatory_on_day_one",
    )
    search_fields = ("title", "description")
    fields = (
        "title",
        "description",
        "type",
        "external_url",
        "file",
        "language",
        "position",
        "is_active",
        "is_mandatory_on_day_one",
        "quiz_question",
        "quiz_expected_answer",
        "created_at",
        "updated_at",
    )
    ordering = ("position",)
    readonly_fields = ("created_at", "updated_at")

    def has_module_permission(self, request):
        return AccessPolicy.is_admin_like(request.user)

    def has_view_permission(self, request, obj=None):
        return AccessPolicy.is_admin_like(request.user)

    def has_add_permission(self, request):
        return AccessPolicy.is_admin_like(request.user)

    def has_change_permission(self, request, obj=None):
        return AccessPolicy.is_admin_like(request.user)

    def has_delete_permission(self, request, obj=None):
        return AccessPolicy.is_super_admin(request.user)


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

    def has_module_permission(self, request):
        return AccessPolicy.is_admin_like(request.user)

    def has_view_permission(self, request, obj=None):
        return AccessPolicy.is_admin_like(request.user)
