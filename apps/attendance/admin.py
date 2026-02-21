from django.contrib import admin

from accounts.access_policy import AccessPolicy
from .models import AttendanceMark, WorkCalendarDay


@admin.register(WorkCalendarDay)
class WorkCalendarDayAdmin(admin.ModelAdmin):
    list_display = ("date", "is_working_day", "is_holiday", "note")
    list_filter = ("is_working_day", "is_holiday")
    search_fields = ("date", "note")
    ordering = ("date",)

    def has_module_permission(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.is_superuser or AccessPolicy.is_admin_like(user)

    def get_model_perms(self, request):
        user = request.user
        allowed = bool(
            user
            and user.is_authenticated
            and (user.is_superuser or user.is_staff or AccessPolicy.is_admin_like(user))
        )
        if not allowed:
            return {}
        return {"add": True, "change": True, "delete": True, "view": True}


@admin.register(AttendanceMark)
class AttendanceMarkAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "status", "created_by", "created_at")
    list_filter = ("status", "date")
    search_fields = ("user__username", "comment")
    ordering = ("-date", "-created_at")

    def has_module_permission(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.is_superuser or AccessPolicy.is_admin_like(user)

    def get_model_perms(self, request):
        user = request.user
        allowed = bool(
            user
            and user.is_authenticated
            and (user.is_superuser or user.is_staff or AccessPolicy.is_admin_like(user))
        )
        if not allowed:
            return {}
        return {"add": True, "change": True, "delete": True, "view": True}
