from django.contrib import admin
from django.contrib.auth import get_user_model
from django.shortcuts import redirect

from accounts.access_policy import AccessPolicy
from .models import AttendanceMark, AttendanceSession, OfficeNetwork, WorkCalendarDay

User = get_user_model()


class SuperAdminOnlyAdminMixin:
    def _can_access(self, request) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and (user.is_superuser or AccessPolicy.is_super_admin(user)))

    def has_module_permission(self, request):
        return self._can_access(request)

    def has_view_permission(self, request, obj=None):
        return self._can_access(request)

    def has_add_permission(self, request):
        return self._can_access(request)

    def has_change_permission(self, request, obj=None):
        return self._can_access(request)

    def has_delete_permission(self, request, obj=None):
        return self._can_access(request)


@admin.register(OfficeNetwork)
class OfficeNetworkAdmin(SuperAdminOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("name", "cidr", "is_active", "created_at", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "cidr")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")


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

    def has_view_permission(self, request, obj=None):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_superuser or AccessPolicy.is_admin_like(user)))

    def has_add_permission(self, request):
        return self.has_view_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_view_permission(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_view_permission(request)


@admin.register(AttendanceMark)
class AttendanceMarkAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "status", "created_by", "created_at")
    list_filter = ("status", "date")
    search_fields = ("user__username", "comment")
    ordering = ("-date", "-created_at")

    def changelist_view(self, request, extra_context=None):
        user = request.user
        if user and user.is_authenticated and not (user.is_superuser or AccessPolicy.is_admin_like(user)):
            return redirect("admin:attendance_attendancemark_add")
        return super().changelist_view(request, extra_context=extra_context)

    def has_module_permission(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return (
            user.is_superuser
            or AccessPolicy.is_admin_like(user)
            or AccessPolicy.is_employee(user)
            or AccessPolicy.is_intern(user)
        )

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

    def has_view_permission(self, request, obj=None):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (
                user.is_superuser
                or AccessPolicy.is_admin_like(user)
                or AccessPolicy.is_employee(user)
                or AccessPolicy.is_intern(user)
            )
        )

    def has_add_permission(self, request):
        return self.has_view_permission(request)

    def has_change_permission(self, request, obj=None):
        if not self.has_view_permission(request):
            return False
        user = request.user
        if obj is None:
            return bool(user and user.is_authenticated and (user.is_superuser or AccessPolicy.is_admin_like(user)))
        return bool(user and user.is_authenticated and (user.is_superuser or AccessPolicy.is_admin_like(user)))

    def has_delete_permission(self, request, obj=None):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_superuser or AccessPolicy.is_admin_like(user)))

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user = request.user
        if not user or not user.is_authenticated:
            return qs.none()
        if user.is_superuser or AccessPolicy.is_admin_like(user):
            return qs
        return qs.filter(user=user)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "user":
            user = request.user
            if user and user.is_authenticated and not (user.is_superuser or AccessPolicy.is_admin_like(user)):
                kwargs["queryset"] = User.objects.filter(id=user.id)
                kwargs["initial"] = user.id
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        user = request.user
        if user and user.is_authenticated and not (user.is_superuser or AccessPolicy.is_admin_like(user)):
            obj.user = user
            if not obj.created_by_id:
                obj.created_by = user
        super().save_model(request, obj, form, change)


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "checked_at", "result", "ip_address", "attendance_mark")
    list_filter = ("result", "checked_at")
    search_fields = ("user__username",)
    ordering = ("-checked_at",)
    readonly_fields = (
        "user",
        "checked_at",
        "ip_address",
        "result",
        "attendance_mark",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_module_permission(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.is_superuser or AccessPolicy.is_admin_like(user)

    def has_view_permission(self, request, obj=None):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_superuser or AccessPolicy.is_admin_like(user)))
