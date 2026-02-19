from django.contrib import admin
from .models import OnboardingReport, OnboardingReportLog


@admin.register(OnboardingReport)
class OnboardingReportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "day",
        "status",
        "reviewer_comment",
        "created_at",
    )

    list_filter = ("status",)
    search_fields = ("user__email", "user__username")
    ordering = ("day__day_number",)

    readonly_fields = (
        "user",
        "day",
        "did",
        "will_do",
        "problems",
        "created_at",
        "updated_at",
    )

    def save_model(self, request, obj, form, change):
        old_status = None

        if change:
            old_obj = OnboardingReport.objects.get(pk=obj.pk)
            old_status = old_obj.status

        super().save_model(request, obj, form, change)

        # Логируем смену статуса
        if change and old_status != obj.status:
            OnboardingReportLog.objects.create(
                report=obj,
                action=obj.status,
                author=request.user,
            )
