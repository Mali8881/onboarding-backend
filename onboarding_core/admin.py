from django.contrib import admin
from .models import OnboardingDay, OnboardingMaterial


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


@admin.register(OnboardingMaterial)
class OnboardingMaterialAdmin(admin.ModelAdmin):
    list_display = ("onboarding_day", "type", "position")
    ordering = ("onboarding_day", "position")
