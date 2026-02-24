from django import forms
from django.contrib import admin
from django.utils.html import format_html

from accounts.access_policy import AccessPolicy
from .models import OnboardingReport, OnboardingReportLog


STATUS_COLORS = {
    OnboardingReport.Status.DRAFT: "#64748b",
    OnboardingReport.Status.SENT: "#2563eb",
    OnboardingReport.Status.ACCEPTED: "#16a34a",
    OnboardingReport.Status.REVISION: "#d97706",
    OnboardingReport.Status.REJECTED: "#dc2626",
}


class OnboardingReportLogInline(admin.TabularInline):
    model = OnboardingReportLog
    extra = 0
    can_delete = False
    readonly_fields = ("action", "author", "created_at")


class OnboardingReportAdminForm(forms.ModelForm):
    class Meta:
        model = OnboardingReport
        fields = "__all__"
        labels = {
            "user": "Стажёр",
            "day": "День онбординга",
            "did": "Что сделал сегодня",
            "will_do": "План на завтра",
            "problems": "Блокеры / вопросы",
            "status": "Статус отчёта",
            "reviewer_comment": "Комментарий наставника",
        }


@admin.register(OnboardingReport)
class OnboardingReportAdmin(admin.ModelAdmin):
    form = OnboardingReportAdminForm
    list_display = ("intern_display", "day_display", "status_badge", "created_at", "updated_at")
    list_filter = ("status", "day")
    search_fields = ("user__email", "user__username", "user__first_name", "user__last_name")
    ordering = ("-created_at",)
    autocomplete_fields = ("user", "day")
    inlines = [OnboardingReportLogInline]

    fieldsets = (
        ("Стажёр и день", {"fields": ("user", "day", "status")}),
        ("Отчёт", {"fields": ("did", "will_do", "problems")}),
        ("Проверка", {"fields": ("reviewer_comment",)}),
        ("Система", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Стажёр")
    def intern_display(self, obj):
        full_name = f"{obj.user.first_name or ''} {obj.user.last_name or ''}".strip()
        return full_name or obj.user.username

    @admin.display(description="День")
    def day_display(self, obj):
        return f"День {obj.day.day_number}: {obj.day.title}"

    @admin.display(description="Статус")
    def status_badge(self, obj):
        color = STATUS_COLORS.get(obj.status, "#64748b")
        return format_html(
            '<span style="padding:4px 10px;border-radius:999px;background:{}22;color:{};font-weight:600;">{}</span>',
            color,
            color,
            obj.get_status_display(),
        )

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


@admin.register(OnboardingReportLog)
class OnboardingReportLogAdmin(admin.ModelAdmin):
    list_display = ("report", "action", "author", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("report__user__username", "report__user__email")
    readonly_fields = ("report", "action", "author", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_module_permission(self, request):
        return AccessPolicy.is_admin_like(request.user)

    def has_view_permission(self, request, obj=None):
        return AccessPolicy.is_admin_like(request.user)
