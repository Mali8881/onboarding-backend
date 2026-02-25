from datetime import date as dt_date
from datetime import timedelta

from django import forms
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.urls import reverse
from django.shortcuts import render
from django.utils import timezone
from django.utils.html import format_html, format_html_join

from accounts.access_policy import AccessPolicy

try:
    from unfold.admin import ModelAdmin
except Exception:
    ModelAdmin = admin.ModelAdmin

from .models import UserWorkSchedule, WeeklyWorkPlan, WorkSchedule
from .services import ensure_user_schedule_for_approved_weekly_plan


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
            "days",
            "online_reason",
            "employee_comment",
            "status",
            "admin_comment",
            "reviewed_by",
            "reviewed_at",
        )
        widgets = {
            "days": forms.Textarea(attrs={"rows": 14, "style": "font-family: monospace;"}),
        }


@admin.register(WorkSchedule)
class WorkScheduleAdmin(ModelAdmin):
    form = WorkScheduleAdminForm
    list_before_template = "admin/work_schedule/workschedule/list_before.html"
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

    def changelist_view(self, request, extra_context=None):
        if not AccessPolicy.is_admin_like(request.user):
            return super().changelist_view(request, extra_context=extra_context)

        requested_week_start = request.GET.get("week_start", "").strip()
        if requested_week_start:
            try:
                week_start = dt_date.fromisoformat(requested_week_start)
            except ValueError:
                week_start = timezone.localdate()
        else:
            week_start = timezone.localdate()
        week_start = week_start - timedelta(days=week_start.weekday())
        week_dates = [week_start + timedelta(days=i) for i in range(7)]
        prev_week_start = week_start - timedelta(days=7)
        next_week_start = week_start + timedelta(days=7)

        user_model = get_user_model()
        employees = user_model.objects.filter(role__name="EMPLOYEE").select_related("role")
        assignments = {
            item.user_id: item
            for item in UserWorkSchedule.objects.select_related("schedule").filter(user__in=employees)
        }

        day_buckets = [[] for _ in range(7)]
        for user in employees:
            assignment = assignments.get(user.id)

            weekly_plan = (
                WeeklyWorkPlan.objects.filter(
                    user=user,
                    week_start=week_start,
                    status=WeeklyWorkPlan.Status.APPROVED,
                )
                .order_by("-updated_at")
                .first()
            )
            # Show only employees with approved weekly plan for this exact week.
            if not weekly_plan:
                continue

            day_map = {}
            for item in (weekly_plan.days or []):
                if isinstance(item, dict) and item.get("date"):
                    day_map[str(item.get("date"))] = item

            user_label = user.get_full_name().strip() or f"Сотрудник #{user.id}"
            if assignment:
                details_url = reverse("admin:work_schedule_userworkschedule_change", args=[assignment.id])
            else:
                details_url = reverse("admin:work_schedule_weeklyworkplan_change", args=[weekly_plan.id])

            for idx, day in enumerate(week_dates):
                item = day_map.get(day.isoformat())
                if not item:
                    continue

                mode = item.get("mode")
                if mode == "day_off":
                    continue
                start_time = item.get("start_time") or "-"
                end_time = item.get("end_time") or "-"
                mode_label = "online" if mode == "online" else "office"

                day_buckets[idx].append(
                    {
                        "user_display": user_label,
                        "time_range": f"{start_time} - {end_time}",
                        "mode": mode_label,
                        "details_url": details_url,
                    }
                )

        for bucket in day_buckets:
            bucket.sort(
                key=lambda item: (
                    0 if item.get("mode") == "office" else 1,
                    (item.get("user_display") or "").lower(),
                )
            )

        context = {
            **self.admin_site.each_context(request),
            "title": "Графики работы: неделя",
            "week_start": week_start,
            "prev_week_url": f"{request.path}?week_start={prev_week_start.isoformat()}",
            "next_week_url": f"{request.path}?week_start={next_week_start.isoformat()}",
            "day_headers": list(
                zip(
                    ("Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"),
                    week_dates,
                )
            ),
            "day_buckets": day_buckets,
        }
        return render(request, "admin/work_schedule_board.html", context)


@admin.register(UserWorkSchedule)
class UserWorkScheduleAdmin(ModelAdmin):
    list_display = (
        "user_full_name",
        "details_button",
        "work_days_display",
        "online_days_display",
        "approval_state_badge",
        "approved_at_display",
    )
    list_filter = ("approved", "requested_at", "schedule")
    search_fields = ("user__username", "user__first_name", "user__last_name", "schedule__name")
    ordering = ("-requested_at",)
    actions = ("mark_approved", "mark_rejected")
    readonly_fields = (
        "user_display_value",
        "schedule_display_value",
        "requested_at",
        "weekly_plan_navigation",
        "latest_weekly_plan_link",
        "weekly_plan_details",
    )
    fieldsets = (
        ("Основное", {"fields": ("user_display_value", "schedule_display_value", "approved", "requested_at")}),
        ("Недельный план сотрудника", {"fields": ("weekly_plan_navigation", "latest_weekly_plan_link", "weekly_plan_details")}),
    )

    def get_form(self, request, obj=None, **kwargs):
        self._current_request = request
        return super().get_form(request, obj, **kwargs)

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("user", "schedule")
        if not AccessPolicy.is_admin_like(request.user):
            return qs.filter(user=request.user)

        user_model = get_user_model()
        employee_qs = user_model.objects.filter(role__name="EMPLOYEE")
        existing_user_ids = set(qs.values_list("user_id", flat=True))
        missing_employees = employee_qs.exclude(id__in=existing_user_ids)
        fallback_schedule = (
            WorkSchedule.objects.filter(is_active=True, is_default=True).first()
            or WorkSchedule.objects.filter(is_active=True).order_by("id").first()
        )
        if fallback_schedule:
            UserWorkSchedule.objects.bulk_create(
                [
                    UserWorkSchedule(user=employee, schedule=fallback_schedule, approved=False)
                    for employee in missing_employees
                ],
                ignore_conflicts=True,
            )
            qs = super().get_queryset(request).select_related("user", "schedule")
        return qs

    def _latest_plan(self, obj):
        return (
            WeeklyWorkPlan.objects.filter(user=obj.user)
            .order_by("-week_start", "-updated_at")
            .first()
        )

    def _selected_week_start(self, obj):
        request = getattr(self, "_current_request", None)
        if request:
            raw_week_start = (request.GET.get("week_start") or "").strip()
            if raw_week_start:
                try:
                    parsed = dt_date.fromisoformat(raw_week_start)
                    return parsed - timedelta(days=parsed.weekday())
                except ValueError:
                    pass

        latest = self._latest_plan(obj)
        if latest and latest.week_start:
            return latest.week_start

        today = timezone.localdate()
        return today - timedelta(days=today.weekday())

    def _plan_for_selected_week(self, obj):
        selected_week_start = self._selected_week_start(obj)
        return (
            WeeklyWorkPlan.objects.filter(user=obj.user, week_start=selected_week_start)
            .order_by("-updated_at")
            .first()
        )

    @admin.display(description="User")
    def user_display_value(self, obj):
        return obj.user.get_full_name().strip() or f"Сотрудник #{obj.user_id}"

    @admin.display(description="Schedule")
    def schedule_display_value(self, obj):
        return "Личный график"

    @admin.display(description="Юзер")
    def user_full_name(self, obj):
        full_name = obj.user.get_full_name().strip()
        return full_name or f"Сотрудник #{obj.user_id}"

    @admin.display(description="Подробности")
    def details_button(self, obj):
        url = reverse("admin:work_schedule_userworkschedule_change", args=[obj.pk])
        return format_html(
            '<a href="{}" style="padding:4px 10px;border:1px solid #d1d5db;border-radius:8px;text-decoration:none;">Подробности</a>',
            url,
        )

    def _collect_mode_days(self, plan, mode):
        labels = []
        for item in (plan.days or []):
            if not isinstance(item, dict):
                continue
            if item.get("mode") != mode:
                continue
            value = item.get("date")
            if not value:
                continue
            try:
                parsed = value if isinstance(value, dt_date) else dt_date.fromisoformat(str(value))
            except ValueError:
                continue
            labels.append(WEEKDAY_SHORT.get(parsed.weekday(), str(parsed.weekday())))
        return labels

    @admin.display(description="Рабочие дни")
    def work_days_display(self, obj):
        plan = self._latest_plan(obj)
        if plan:
            office_days = self._collect_mode_days(plan, "office")
            if office_days:
                return ", ".join(office_days)
        labels = {num: label for num, label in WEEKDAY_CHOICES}
        if obj.schedule_id and isinstance(obj.schedule.work_days, list):
            return ", ".join(labels.get(day, str(day)) for day in obj.schedule.work_days)
        return "-"

    @admin.display(description="Онлайн дни")
    def online_days_display(self, obj):
        plan = self._latest_plan(obj)
        if not plan:
            return "-"
        online_days = self._collect_mode_days(plan, "online")
        return ", ".join(online_days) if online_days else "-"

    @admin.display(description="Утвержденный недельный план")
    def approval_state_badge(self, obj):
        plan = self._latest_plan(obj)
        if obj.approved or (plan and plan.status == WeeklyWorkPlan.Status.APPROVED):
            return format_html('<span style="color:#16a34a;font-weight:700;">●</span>')
        if plan and plan.status in {
            WeeklyWorkPlan.Status.PENDING,
            WeeklyWorkPlan.Status.CLARIFICATION_REQUESTED,
        }:
            return format_html('<span style="color:#d97706;font-weight:700;">●</span>')
        return format_html('<span style="color:#dc2626;font-weight:700;">●</span>')

    @admin.display(description="Время утверждения недельного плана")
    def approved_at_display(self, obj):
        plan = self._latest_plan(obj)
        if not plan or plan.status != WeeklyWorkPlan.Status.APPROVED or not plan.reviewed_at:
            return "-"
        local_dt = timezone.localtime(plan.reviewed_at)
        return local_dt.strftime("%d.%m.%Y %H:%M")

    @admin.display(description="Недельный план")
    def latest_weekly_plan_link(self, obj):
        plan = self._plan_for_selected_week(obj)
        if not plan:
            return "Нет недельного плана за выбранную неделю"
        url = reverse("admin:work_schedule_weeklyworkplan_change", args=[plan.pk])
        return format_html('<a href="{}">Неделя {} (открыть)</a>', url, plan.week_start)

    @admin.display(description="Навигация недели")
    def weekly_plan_navigation(self, obj):
        request = getattr(self, "_current_request", None)
        if not request:
            return "-"

        selected_week_start = self._selected_week_start(obj)
        prev_week = selected_week_start - timedelta(days=7)
        next_week = selected_week_start + timedelta(days=7)
        base_path = request.path
        prev_url = f"{base_path}?week_start={prev_week.isoformat()}"
        next_url = f"{base_path}?week_start={next_week.isoformat()}"
        return format_html(
            '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">'
            '<a href="{}" style="padding:4px 10px;border:1px solid #d1d5db;border-radius:8px;text-decoration:none;">← Предыдущая неделя</a>'
            '<span style="color:#334155;">Текущая: {}</span>'
            '<a href="{}" style="padding:4px 10px;border:1px solid #d1d5db;border-radius:8px;text-decoration:none;">Следующая неделя →</a>'
            "</div>",
            prev_url,
            selected_week_start.isoformat(),
            next_url,
        )

    @admin.display(description="Детально по дням")
    def weekly_plan_details(self, obj):
        plan = self._plan_for_selected_week(obj)
        if not plan:
            return "Нет данных"

        by_date = sorted(
            [item for item in (plan.days or []) if isinstance(item, dict)],
            key=lambda item: str(item.get("date", "")),
        )
        if not by_date:
            return "Нет данных"

        rows = []
        for item in by_date:
            day = item.get("date", "-")
            mode = item.get("mode", "")
            if mode == "day_off":
                slot = "Выходной"
            else:
                slot = f"{item.get('start_time', '-')} - {item.get('end_time', '-')}"
            breaks = item.get("breaks") or []
            breaks_text = ", ".join(
                f"{part.get('start_time', '-')}-{part.get('end_time', '-')}"
                for part in breaks
                if isinstance(part, dict)
            ) or "-"
            lunch_start = item.get("lunch_start")
            lunch_end = item.get("lunch_end")
            lunch_text = f"{lunch_start}-{lunch_end}" if lunch_start and lunch_end else "-"
            rows.append((day, slot, mode or "-", breaks_text, lunch_text))

        return format_html(
            '<div style="display:grid;gap:4px;">{}</div>',
            format_html_join(
                "",
                '<div><strong>{}</strong>: {} <span style="color:#64748b;">({})</span> | Перерывы: {} | Обед: {}</div>',
                rows,
            ),
        )

    @admin.action(description="Подтвердить выбранные запросы")
    def mark_approved(self, request, queryset):
        if not AccessPolicy.is_admin_like(request.user):
            self.message_user(request, "Недостаточно прав.", level=messages.ERROR)
            return
        updated = queryset.update(approved=True)
        self.message_user(request, f"Подтверждено запросов: {updated}")

    @admin.action(description="Отклонить выбранные запросы")
    def mark_rejected(self, request, queryset):
        if not AccessPolicy.is_admin_like(request.user):
            self.message_user(request, "Недостаточно прав.", level=messages.ERROR)
            return
        updated = queryset.update(approved=False)
        self.message_user(request, f"Отклонено запросов: {updated}")

    def has_module_permission(self, request):
        return AccessPolicy.is_admin_like(request.user)

    def has_view_permission(self, request, obj=None):
        return AccessPolicy.is_admin_like(request.user)

    def has_add_permission(self, request):
        return False

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
        updated = 0
        for plan in queryset.select_related("user"):
            plan.status = WeeklyWorkPlan.Status.APPROVED
            plan.reviewed_by = request.user
            plan.reviewed_at = timezone.now()
            plan.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
            ensure_user_schedule_for_approved_weekly_plan(plan)
            updated += 1
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
        if AccessPolicy.is_admin_like(request.user) and obj.status == WeeklyWorkPlan.Status.APPROVED:
            ensure_user_schedule_for_approved_weekly_plan(obj)


