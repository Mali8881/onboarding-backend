from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.html import format_html

from accounts.access_policy import AccessPolicy
from .models import OnboardingDay, OnboardingMaterial, OnboardingProgress


PROGRESS_COLORS = {
    OnboardingProgress.Status.NOT_STARTED: "#64748b",
    OnboardingProgress.Status.IN_PROGRESS: "#2563eb",
    OnboardingProgress.Status.DONE: "#16a34a",
}


class OnboardingDayAdminForm(forms.ModelForm):
    class Meta:
        model = OnboardingDay
        fields = "__all__"
        labels = {
            "day_number": "Номер дня",
            "title": "Название дня",
            "goals": "Цели дня",
            "description": "Описание",
            "instructions": "Инструкции для стажера",
            "deadline_time": "Дедлайн (время)",
            "regulations": "Обязательные регламенты",
            "is_active": "Активен",
            "position": "Порядок отображения",
        }
        help_texts = {
            "day_number": "Порядковый номер (1, 2, 3...).",
            "title": "Короткое понятное название дня.",
            "goals": "Что стажер должен достичь в этот день.",
            "description": "Подробное описание задач дня.",
            "instructions": "Пошаговые указания, что делать.",
            "deadline_time": "До какого времени нужно завершить задачи дня.",
            "regulations": "Отметь документы, с которыми стажер обязан ознакомиться.",
            "position": "Чем меньше число, тем выше в списке.",
        }
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Например: Первый рабочий день"}),
            "goals": forms.Textarea(attrs={"rows": 3, "placeholder": "Например: Получить доступы и пройти вводный инструктаж"}),
            "description": forms.Textarea(attrs={"rows": 4, "placeholder": "Опиши программу дня простым языком"}),
            "instructions": forms.Textarea(attrs={"rows": 4, "placeholder": "Пошагово: 1) ... 2) ... 3) ..."}),
            "deadline_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def clean_title(self):
        title = (self.cleaned_data.get("title") or "").strip()
        if len(title) < 3:
            raise ValidationError("Название слишком короткое (минимум 3 символа).")
        return title


class OnboardingMaterialAdminForm(forms.ModelForm):
    class Meta:
        model = OnboardingMaterial
        fields = "__all__"
        labels = {
            "day": "День онбординга",
            "type": "Тип материала",
            "content": "Содержимое",
            "position": "Порядок",
        }
        help_texts = {
            "type": "Выбери формат материала: ссылка, видео, текст, изображение или файл.",
            "content": "Для LINK/VIDEO укажи URL. Для TEXT добавь текст инструкции.",
            "position": "Чем меньше число, тем выше материал в списке.",
        }
        widgets = {
            "content": forms.Textarea(attrs={"rows": 4, "placeholder": "Вставь ссылку или текст материала"}),
        }

    def clean(self):
        cleaned = super().clean()
        material_type = cleaned.get("type")
        content = (cleaned.get("content") or "").strip()

        if len(content) < 3:
            self.add_error("content", "Заполни содержимое материала (минимум 3 символа).")

        if material_type in {OnboardingMaterial.MaterialType.LINK, OnboardingMaterial.MaterialType.VIDEO}:
            if not (content.startswith("http://") or content.startswith("https://")):
                self.add_error("content", "Для ссылки/видео укажи корректный URL (http:// или https://).")

        return cleaned


class OnboardingProgressAdminForm(forms.ModelForm):
    class Meta:
        model = OnboardingProgress
        fields = "__all__"
        labels = {
            "user": "Пользователь",
            "day": "День онбординга",
            "status": "Статус",
            "completed_at": "Дата завершения",
        }
        widgets = {
            "completed_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        completed_at = cleaned.get("completed_at")

        if status == OnboardingProgress.Status.DONE and not completed_at:
            cleaned["completed_at"] = timezone.now()

        if status != OnboardingProgress.Status.DONE and completed_at:
            cleaned["completed_at"] = None

        return cleaned


class OnboardingMaterialInline(admin.TabularInline):
    model = OnboardingMaterial
    form = OnboardingMaterialAdminForm
    extra = 1
    ordering = ("position",)
    fields = ("position", "type", "content")


@admin.register(OnboardingDay)
class OnboardingDayAdmin(admin.ModelAdmin):
    form = OnboardingDayAdminForm
    list_display = ("day_number", "title", "materials_count", "is_active", "position")
    list_filter = ("is_active",)
    search_fields = ("title", "goals", "description", "instructions")
    ordering = ("position", "day_number")
    filter_horizontal = ("regulations",)
    inlines = [OnboardingMaterialInline]

    fieldsets = (
        ("Основное", {"fields": ("day_number", "title", "is_active", "position")}),
        ("Контент дня", {"fields": ("goals", "description", "instructions")}),
        ("Регламенты", {"fields": ("regulations",)}),
        ("Дедлайн", {"fields": ("deadline_time",)}),
    )

    @admin.display(description="Материалов")
    def materials_count(self, obj):
        return obj.materials.count()

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


@admin.register(OnboardingMaterial)
class OnboardingMaterialAdmin(admin.ModelAdmin):
    form = OnboardingMaterialAdminForm
    list_display = ("day", "type_badge", "position", "short_content")
    list_filter = ("type", "day")
    search_fields = ("content", "day__title")
    ordering = ("day", "position")
    autocomplete_fields = ("day",)

    @admin.display(description="Тип")
    def type_badge(self, obj):
        colors = {"link": "#2563eb", "video": "#d97706", "text": "#059669", "image": "#7c3aed", "file": "#0f766e"}
        color = colors.get(obj.type, "#64748b")
        return format_html(
            '<span style="padding:4px 10px;border-radius:999px;background:{}22;color:{};font-weight:600;">{}</span>',
            color,
            color,
            obj.get_type_display(),
        )

    @admin.display(description="Контент")
    def short_content(self, obj):
        value = (obj.content or "").strip()
        return value if len(value) <= 70 else f"{value[:67]}..."

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


@admin.register(OnboardingProgress)
class OnboardingProgressAdmin(admin.ModelAdmin):
    form = OnboardingProgressAdminForm
    list_display = ("user", "day", "status_badge", "completed_at", "updated_at")
    list_filter = ("status", "day")
    search_fields = ("user__email", "user__username", "user__first_name", "user__last_name")
    autocomplete_fields = ("user", "day")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-updated_at",)

    @admin.display(description="Статус")
    def status_badge(self, obj):
        color = PROGRESS_COLORS.get(obj.status, "#64748b")
        return format_html(
            '<span style="padding:4px 10px;border-radius:999px;background:{}22;color:{};font-weight:600;">{}</span>',
            color,
            color,
            obj.get_status_display(),
        )

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
