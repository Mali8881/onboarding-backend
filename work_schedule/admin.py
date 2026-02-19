from django.contrib import admin
from .models import (
    WorkSchedule,
    ProductionCalendar,
    UserWorkSchedule,
)

@admin.register(ProductionCalendar)
class ProductionCalendarAdmin(admin.ModelAdmin):
    list_display = ("date", "is_working_day", "is_holiday")
    list_filter = ("is_holiday", "is_working_day")
    ordering = ("date",)

@admin.register(WorkSchedule)
class WorkScheduleAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "is_default")
    list_filter = ("is_active", "is_default")
    search_fields = ("name",)


@admin.register(UserWorkSchedule)
class UserWorkScheduleAdmin(admin.ModelAdmin):
    list_display = ("user", "schedule", "approved", "requested_at")
    list_filter = ("approved",)
    search_fields = ("user__username",)
