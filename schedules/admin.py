from django.contrib import admin
from .models import WorkSchedule

@admin.register(WorkSchedule)
class WorkScheduleAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active")
