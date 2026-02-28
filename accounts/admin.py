from django import forms
from django.contrib import admin, messages
from django.contrib.admin.sites import NotRegistered
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group
from django.utils.html import format_html

from .access_policy import AccessPolicy
from .models import AuditLog, Department, LoginHistory, Permission, Position, Role, User


ROLE_BADGE_COLORS = {
    Role.Name.SUPER_ADMIN: "#d97706",
    Role.Name.ADMINISTRATOR: "#0ea5e9",
    Role.Name.ADMIN: "#2563eb",
    Role.Name.EMPLOYEE: "#059669",
    Role.Name.INTERN: "#7c3aed",
}


def is_super_admin(user):
    return AccessPolicy.is_super_admin(user)


def is_admin(user):
    return AccessPolicy.is_admin_like(user)


def can_manage_users(user):
    return AccessPolicy.is_super_admin(user) or AccessPolicy.is_administrator(user)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = (
        "username",
        "full_name_display",
        "role_badge",
        "org_display",
        "status_badge",
        "manager",
    )
    list_filter = (
        "role",
        "department",
        "position",
        "is_active",
        "is_blocked",
        "is_staff",
    )
    search_fields = (
        "username",
        "first_name",
        "last_name",
        "email",
        "telegram",
        "phone",
        "custom_position",
    )
    ordering = ("id",)
    list_select_related = ("role", "department", "position", "manager")
    autocomplete_fields = ("role", "department", "position", "manager")
    readonly_fields = ("last_login", "date_joined", "failed_login_attempts", "lockout_until")
    filter_horizontal = ()

    fieldsets = (
        ("Учетная запись", {"fields": ("username", "password")} ),
        (
            "Личные данные",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "phone",
                    "telegram",
                    "photo",
                )
            },
        ),
        (
            "Оргструктура и роль",
            {
                "fields": (
                    "role",
                    "department",
                    "position",
                    "custom_position",
                    "manager",
                )
            },
        ),
        (
            "Доступ",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_blocked",
                )
            },
        ),
        (
            "Системные поля",
            {
                "fields": (
                    "last_login",
                    "date_joined",
                    "failed_login_attempts",
                    "lockout_until",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    add_fieldsets = (
        (
            "Создание пользователя",
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "password1",
                    "password2",
                    "first_name",
                    "last_name",
                    "email",
                    "role",
                    "department",
                    "position",
                    "custom_position",
                    "manager",
                    "is_active",
                    "is_staff",
                ),
            },
        ),
    )

    exclude = ("groups", "user_permissions", "is_superuser")
    actions = ("set_active", "set_inactive", "block_users", "unblock_users")

    @admin.display(description="ФИО")
    def full_name_display(self, obj):
        full_name = f"{obj.first_name or ''} {obj.last_name or ''}".strip()
        return full_name or "-"

    @admin.display(description="Роль")
    def role_badge(self, obj):
        role_name = obj.role.name if obj.role_id else "-"
        color = ROLE_BADGE_COLORS.get(role_name, "#64748b")
        return format_html(
            '<span style="padding:4px 10px;border-radius:999px;background:{}22;color:{};font-weight:600;">{}</span>',
            color,
            color,
            role_name,
        )

    @admin.display(description="Подразделение / должность")
    def org_display(self, obj):
        department = obj.department.name if obj.department_id else "-"
        position = obj.position.name if obj.position_id else (obj.custom_position or "-")
        return f"{department} / {position}"

    @admin.display(description="Статус")
    def status_badge(self, obj):
        if obj.is_blocked:
            return format_html('<span style="color:#dc2626;font-weight:600;">● Заблокирован</span>')
        if obj.is_active:
            return format_html('<span style="color:#16a34a;font-weight:600;">● Активен</span>')
        return format_html('<span style="color:#64748b;font-weight:600;">● Неактивен</span>')

    @admin.action(description="Сделать активными")
    def set_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Активировано пользователей: {updated}")

    @admin.action(description="Сделать неактивными")
    def set_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Деактивировано пользователей: {updated}", level=messages.WARNING)

    @admin.action(description="Заблокировать")
    def block_users(self, request, queryset):
        updated = queryset.update(is_blocked=True)
        self.message_user(request, f"Заблокировано пользователей: {updated}", level=messages.WARNING)

    @admin.action(description="Разблокировать")
    def unblock_users(self, request, queryset):
        updated = queryset.update(is_blocked=False)
        self.message_user(request, f"Разблокировано пользователей: {updated}")

    def has_module_permission(self, request):
        return can_manage_users(request.user)

    def has_view_permission(self, request, obj=None):
        return can_manage_users(request.user)

    def has_add_permission(self, request):
        return can_manage_users(request.user)

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if not request.user.is_authenticated:
            return qs.none()

        if not can_manage_users(request.user):
            return qs.none()

        return qs

    def has_change_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False

        if obj is None:
            return can_manage_users(request.user)

        if not can_manage_users(request.user):
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False

        if not can_manage_users(request.user):
            return False

        return super().has_delete_permission(request, obj)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "role":
            qs = Role.objects.all().order_by("level")
            if is_admin(request.user):
                qs = qs.exclude(name=Role.Name.SUPER_ADMIN)
            kwargs["queryset"] = qs
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    class RoleAdminForm(forms.ModelForm):
        class Meta:
            model = Role
            fields = "__all__"
            labels = {
                "name": "Системная роль",
                "level": "Уровень доступа",
                "description": "Описание",
                "permissions": "Права доступа",
            }
            help_texts = {
                "name": "Допустимы только: SUPER_ADMIN, ADMINISTRATOR, ADMIN, EMPLOYEE, INTERN.",
                "permissions": "Права назначаются на уровне роли и применяются ко всем пользователям этой роли.",
            }
            widgets = {
                "description": forms.Textarea(
                    attrs={"rows": 3, "placeholder": "Кратко опиши назначение роли"}
                ),
            }

        def clean_name(self):
            value = (self.cleaned_data.get("name") or "").strip().upper()
            allowed = {
                Role.Name.SUPER_ADMIN,
                Role.Name.ADMINISTRATOR,
                Role.Name.ADMIN,
                Role.Name.EMPLOYEE,
                Role.Name.INTERN,
            }
            if value not in allowed:
                raise forms.ValidationError(
                    "Допустимы только SUPER_ADMIN, ADMINISTRATOR, ADMIN, EMPLOYEE, INTERN."
                )
            return value

    form = RoleAdminForm
    list_display = ("name", "level", "permissions_count", "users_count")
    search_fields = ("name", "description", "permissions__codename")
    list_filter = ("level",)
    filter_horizontal = ("permissions",)
    readonly_fields = ("users_count",)
    fieldsets = (
        ("Основное", {"fields": ("name", "level", "description")}),
        ("Права", {"fields": ("permissions",)}),
        ("Статистика", {"fields": ("users_count",), "classes": ("collapse",)}),
    )

    @admin.display(description="Количество прав")
    def permissions_count(self, obj):
        return obj.permissions.count()

    @admin.display(description="Пользователей с ролью")
    def users_count(self, obj):
        return obj.user_set.count()

    def has_module_permission(self, request):
        return AccessPolicy.can_access_admin_panel(request.user)

    def has_view_permission(self, request, obj=None):
        return AccessPolicy.can_access_admin_panel(request.user)

    def has_change_permission(self, request, obj=None):
        return is_super_admin(request.user)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if is_admin(request.user):
            return qs.exclude(name=Role.Name.SUPER_ADMIN)
        return qs


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("codename", "module")
    search_fields = ("codename", "module")

    def has_module_permission(self, request):
        return is_super_admin(request.user)

    def get_model_perms(self, request):
        # Hide from admin sidebar/index; keep model available for RBAC internals.
        return {}


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "action", "category", "level", "object_type", "object_id")
    list_filter = ("level", "category", "created_at")
    search_fields = ("action", "object_type", "object_id", "user__username")
    readonly_fields = (
        "user",
        "action",
        "category",
        "level",
        "object_type",
        "object_id",
        "ip_address",
        "created_at",
    )

    def has_module_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return AccessPolicy.has_permission(request.user, "logs_read")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "is_active", "users_count")
    list_filter = ("is_active", "parent")
    search_fields = ("name",)
    autocomplete_fields = ("parent",)

    @admin.display(description="Сотрудников")
    def users_count(self, obj):
        return obj.user_set.count()

    def has_module_permission(self, request):
        return AccessPolicy.can_access_admin_panel(request.user)

    def has_view_permission(self, request, obj=None):
        return AccessPolicy.can_access_admin_panel(request.user)

    def has_add_permission(self, request):
        return AccessPolicy.can_manage_org_reference(request.user)

    def has_change_permission(self, request, obj=None):
        return AccessPolicy.can_manage_org_reference(request.user)

    def has_delete_permission(self, request, obj=None):
        return AccessPolicy.can_manage_org_reference(request.user)

    def get_model_perms(self, request):
        # Hide from admin sidebar/index but keep model in DB.
        return {}

    def delete_model(self, request, obj):
        if obj.user_set.exists():
            self.message_user(
                request,
                "Нельзя удалить отдел: к нему привязаны пользователи.",
                level=messages.ERROR,
            )
            return
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        blocked = queryset.filter(user__isnull=False).distinct()
        if blocked.exists():
            self.message_user(
                request,
                "Некоторые отделы не удалены: к ним привязаны пользователи.",
                level=messages.ERROR,
            )
            queryset = queryset.exclude(pk__in=blocked.values_list("pk", flat=True))
        super().delete_queryset(request, queryset)


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)

    def has_module_permission(self, request):
        return AccessPolicy.can_access_admin_panel(request.user)

    def has_view_permission(self, request, obj=None):
        return AccessPolicy.can_access_admin_panel(request.user)

    def has_add_permission(self, request):
        return AccessPolicy.can_manage_org_reference(request.user)

    def has_change_permission(self, request, obj=None):
        return AccessPolicy.can_manage_org_reference(request.user)

    def has_delete_permission(self, request, obj=None):
        return AccessPolicy.can_manage_org_reference(request.user)


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "ip_address", "success")
    list_filter = ("success", "created_at")
    search_fields = ("user__username", "ip_address", "user_agent")
    readonly_fields = ("user", "ip_address", "user_agent", "success", "created_at")

    def has_module_permission(self, request):
        return is_super_admin(request.user)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


try:
    admin.site.unregister(Group)
except NotRegistered:
    pass




