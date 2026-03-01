from django.contrib import admin

from accounts.access_policy import AccessPolicy

from .models import (
    Regulation,
    RegulationQuiz,
)

class RegulationQuizInline(admin.StackedInline):
    model = RegulationQuiz
    extra = 0
    max_num = 1


@admin.register(Regulation)
class RegulationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "type",
        "is_active",
        "is_mandatory_on_day_one",
        "read_deadline_at",
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
    inlines = (RegulationQuizInline,)

    def has_module_permission(self, request):
        return AccessPolicy.is_admin_like(request.user)

    def has_view_permission(self, request, obj=None):
        return AccessPolicy.is_admin_like(request.user)

    def has_add_permission(self, request):
        return AccessPolicy.is_admin_like(request.user)

    def has_change_permission(self, request, obj=None):
        return AccessPolicy.is_admin_like(request.user)

    def has_delete_permission(self, request, obj=None):
        return AccessPolicy.is_admin_like(request.user)
