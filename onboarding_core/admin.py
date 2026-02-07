from django.contrib import admin
from .models import OnboardingDay, OnboardingMaterial, OnboardingProgress


class OnboardingMaterialInline(admin.TabularInline):
    model = OnboardingMaterial
    extra = 1
    ordering = ("position",)


@admin.register(OnboardingDay)
class OnboardingDayAdmin(admin.ModelAdmin):
    list_display = ("day_number", "title", "is_active", "position")
    list_filter = ("is_active",)
    ordering = ("position", "day_number")
    inlines = [OnboardingMaterialInline]

    fieldsets = (
        ("Основное", {
            "fields": (
                "day_number",
                "title",
                "is_active",
                "position",
            )
        }),
        ("Контент дня", {
            "fields": (
                "goals",
                "description",
                "instructions",
            )
        }),
        ("Дедлайн", {
            "fields": (
                "deadline_time",
            )
        }),
    )


@admin.register(OnboardingMaterial)
class OnboardingMaterialAdmin(admin.ModelAdmin):
    list_display = ("day", "type", "position")
    list_filter = ("type",)
    ordering = ("day", "position")


@admin.register(OnboardingProgress)
class OnboardingProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "day", "status", "completed_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("user__email", "user__username")
