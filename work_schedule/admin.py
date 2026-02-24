from django import forms
from django.contrib import admin, messages
from django.db import transaction
from django.utils.html import format_html

from accounts.access_policy import AccessPolicy

try:
    from unfold.admin import ModelAdmin
except Exception:
    ModelAdmin = admin.ModelAdmin

from .models import WorkSchedule


WEEKDAY_CHOICES = (
    (0, "Пн"),
    (1, "Вт"),
    (2, "Ср"),
    (3, "Чт"),
    (4, "Пт"),
    (5, "Сб"),
    (6, "Вс"),
)


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
