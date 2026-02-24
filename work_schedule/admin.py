from django import forms
from django.contrib import admin, messages
from django.db import transaction
from django.utils import timezone
from django.utils.html import format_html

from accounts.access_policy import AccessPolicy

try:
    from unfold.admin import ModelAdmin
except Exception:
    ModelAdmin = admin.ModelAdmin

from .models import WeeklyWorkPlan, WorkSchedule


WEEKDAY_CHOICES = (
    (0, "Пн"),
    (1, "Вт"),
    (2, "Ср"),
    (3, "Чт"),
    (4, "Пт"),
    (5, "Сб"),
    (6, "Вс"),
)
WEEKDAY_SHORT = {
    0: "Пн",
    1: "Вт",
    2: "Ср",
    3: "Чт",
    4: "Пт",
    5: "Сб",
    6: "Вс",
}


class WorkScheduleAdminForm(forms.ModelForm):
    work_days = forms.MultipleChoiceField(
        label="Рабочие дни",
        choices=WEEKDAY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
    )

    start_time = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}, format="%H:%M"), input_formats=["%H:%M", "%H:%M:%S"])
    end_time = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}, format="%H:%M"), input_formats=["%H:%M", "%H:%M:%S"])
    break_start = forms.TimeField(required=False, widget=forms.TimeInput(attrs={"type": "time"}, format="%H:%M"), input_formats=["%H:%M", "%H:%M:%S"])
    break_end = forms.TimeField(required=False, widget=forms.TimeInput(attrs={"type": "time"}, format="%H:%M"), input_formats=["%H:%M", "%H:%M:%S"])

    class Meta:
        model = WorkSchedule
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.work_days:
            self.initial["work_days"] = [str(day) for day in self.instance.work_days]
        elif not self.instance.pk:
            self.initial["work_days"] = ["0", "1", "2", "3", "4"]

    def clean_work_days(self):
        values = self.cleaned_data.get("work_days") or []
        cleaned = sorted({int(day) for day in values})
        if not cleaned:
            raise forms.ValidationError("Выберите хотя бы один рабочий день.")
        return cleaned


class WeeklyWorkPlanAdminForm(forms.ModelForm):
    class Meta:
        model = WeeklyWorkPlan
        fields = (
            "user",
            "week_start",
            "online_reason",
            "employee_comment",
            "status",
            "admin_comment",
            "reviewed_by",
            "reviewed_at",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        days_map = {
            item.get("day"): item for item in (self.instance.days or [])
            if isinstance(item, dict) and isinstance(item.get("day"), int)
        }
        for day in range(7):
            item = days_map.get(day, {})
            self.fields[f"day_{day}_office"] = forms.IntegerField(
                label=f"{WEEKDAY_SHORT[day]}: офис часы",
                min_value=0,
                initial=item.get("office_hours", 0),
                required=True,
            )
            self.fields[f"day_{day}_online"] = forms.IntegerField(
                label=f"{WEEKDAY_SHORT[day]}: онлайн часы",
                min_value=0,
                initial=item.get("online_hours", 0),
                required=True,
            )
            self.fields[f"day_{day}_comment"] = forms.CharField(
                label=f"{WEEKDAY_SHORT[day]}: комментарий",
                required=False,
                initial=item.get("comment", ""),
            )

    def clean(self):
        cleaned = super().clean()
        days = []
        for day in range(7):
            days.append(
                {
                    "day": day,
                    "office_hours": cleaned.get(f"day_{day}_office", 0),
                    "online_hours": cleaned.get(f"day_{day}_online", 0),
                    "comment": cleaned.get(f"day_{day}_comment", ""),
                }
            )
        cleaned["days"] = days
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.days = self.cleaned_data["days"]
        if commit:
            instance.save()
            self.save_m2m()
        return instance


@admin.register(WorkSchedule)
class WorkScheduleAdmin(ModelAdmin):
    form = WorkScheduleAdminForm
    list_display = ("name", "work_days_display", "work_time_display", "users_count", "status_badge")
    list_filter = ("is_active", "is_default")
    search_fields = ("name",)
    ordering = ("name",)
    actions = ("activate_selected", "deactivate_selected", "set_default_selected")

    @admin.display(description="Рабочие дни")
    def work_days_display(self, obj):
        labels = {num: label for num, label in WEEKDAY_CHOICES}
        return ", ".join(labels.get(day, str(day)) for day in (obj.work_days or []))

    @admin.display(description="Время работы")
    def work_time_display(self, obj):
        return f"{obj.start_time.strftime('%H:%M')} - {obj.end_time.strftime('%H:%M')}"

    @admin.display(description="Сотрудники")
    def users_count(self, obj):
        return obj.users.count()

    @admin.display(description="Статус")
    def status_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color:#16a34a;font-weight:600;">● Активен</span>')
        return format_html('<span style="color:#64748b;font-weight:600;">● Неактивен</span>')

    @admin.action(description="Активировать выбранные")
    def activate_selected(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Активировано графиков: {updated}")

    @admin.action(description="Деактивировать выбранные")
    def deactivate_selected(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Деактивировано графиков: {updated}", level=messages.WARNING)

    @admin.action(description="Сделать выбранный график базовым")
    def set_default_selected(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Выберите ровно один график для установки по умолчанию.", level=messages.ERROR)
            return

        target = queryset.first()
        with transaction.atomic():
            WorkSchedule.objects.filter(is_default=True).exclude(pk=target.pk).update(is_default=False)
            target.is_default = True
            target.save(update_fields=["is_default"])
        self.message_user(request, f"График '{target.name}' установлен как базовый.")

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


@admin.register(WeeklyWorkPlan)
class WeeklyWorkPlanAdmin(ModelAdmin):
    form = WeeklyWorkPlanAdminForm
    list_display = (
        "week_start",
        "user",
        "office_hours",
        "online_hours",
        "status",
        "reviewed_by",
        "updated_at",
    )
    list_filter = ("status", "week_start")
    search_fields = ("user__username", "online_reason", "employee_comment", "admin_comment")
    ordering = ("-week_start", "-updated_at")
    actions = ("mark_approved", "mark_clarification_requested", "mark_rejected")

    @admin.action(description="Approve selected plans")
    def mark_approved(self, request, queryset):
        if not AccessPolicy.is_admin_like(request.user):
            self.message_user(request, "Недостаточно прав.", level=messages.ERROR)
            return
        updated = queryset.update(
            status=WeeklyWorkPlan.Status.APPROVED,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )
        self.message_user(request, f"Подтверждено планов: {updated}")

    @admin.action(description="Request clarification for selected plans")
    def mark_clarification_requested(self, request, queryset):
        if not AccessPolicy.is_admin_like(request.user):
            self.message_user(request, "Недостаточно прав.", level=messages.ERROR)
            return
        updated = queryset.update(
            status=WeeklyWorkPlan.Status.CLARIFICATION_REQUESTED,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )
        self.message_user(request, f"Отправлено на уточнение: {updated}")

    @admin.action(description="Reject selected plans")
    def mark_rejected(self, request, queryset):
        if not AccessPolicy.is_admin_like(request.user):
            self.message_user(request, "Недостаточно прав.", level=messages.ERROR)
            return
        updated = queryset.update(
            status=WeeklyWorkPlan.Status.REJECTED,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )
        self.message_user(request, f"Отклонено планов: {updated}")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if AccessPolicy.is_admin_like(request.user):
            return qs
        return qs.filter(user=request.user)

    def get_readonly_fields(self, request, obj=None):
        if AccessPolicy.is_admin_like(request.user):
            return ("submitted_at", "updated_at")
        return (
            "user",
            "status",
            "admin_comment",
            "reviewed_by",
            "reviewed_at",
            "submitted_at",
            "updated_at",
        )

    def has_module_permission(self, request):
        return bool(request.user and request.user.is_authenticated)

    def has_view_permission(self, request, obj=None):
        if not request.user or not request.user.is_authenticated:
            return False
        if AccessPolicy.is_admin_like(request.user):
            return True
        if obj is None:
            return True
        return obj.user_id == request.user.id

    def has_add_permission(self, request):
        return bool(request.user and request.user.is_authenticated)

    def has_change_permission(self, request, obj=None):
        if not request.user or not request.user.is_authenticated:
            return False
        if AccessPolicy.is_admin_like(request.user):
            return True
        if obj is None:
            return True
        return obj.user_id == request.user.id

    def has_delete_permission(self, request, obj=None):
        if not request.user or not request.user.is_authenticated:
            return False
        if AccessPolicy.is_admin_like(request.user):
            return True
        if obj is None:
            return True
        return obj.user_id == request.user.id and obj.status in {
            WeeklyWorkPlan.Status.PENDING,
            WeeklyWorkPlan.Status.CLARIFICATION_REQUESTED,
        }

    def save_model(self, request, obj, form, change):
        if not AccessPolicy.is_admin_like(request.user):
            obj.user = request.user
            obj.status = WeeklyWorkPlan.Status.PENDING
            obj.admin_comment = ""
            obj.reviewed_by = None
            obj.reviewed_at = None
        super().save_model(request, obj, form, change)
