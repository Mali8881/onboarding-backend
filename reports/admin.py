from django.contrib import admin
from .models import OnboardingReport


@admin.register(OnboardingReport)
class OnboardingReportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "day",
        "status",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("user__email", "user__username")
    ordering = ("day__day_number",)

