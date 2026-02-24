from django import forms
from django.contrib import admin
from django.utils.html import format_html

from accounts.access_policy import AccessPolicy
from .models import Feedback, Instruction, News


class FeedbackAdminForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = "__all__"
        labels = {
            "is_anonymous": "Анонимно",
            "full_name": "ФИО сотрудника",
            "contact": "Контакт (email/телефон)",
            "type": "Тип обращения",
            "text": "Сообщение",
            "status": "Статус",
            "is_read": "Прочитано",
        }
        help_texts = {
            "full_name": "Заполняется только если обращение не анонимное.",
            "contact": "Опционально, для обратной связи.",
            "text": "Кратко опишите суть обращения.",
        }
        widgets = {
            "text": forms.Textarea(attrs={"rows": 6, "placeholder": "Опишите проблему, предложение или отзыв"}),
            "full_name": forms.TextInput(attrs={"placeholder": "Например: Иванов Иван"}),
            "contact": forms.TextInput(attrs={"placeholder": "email или телефон"}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("is_anonymous"):
            cleaned["full_name"] = ""
            cleaned["contact"] = ""
        else:
            if not (cleaned.get("full_name") or "").strip():
                self.add_error("full_name", "Для неанонимного обращения укажите ФИО.")
        return cleaned


class InstructionAdminForm(forms.ModelForm):
    class Meta:
        model = Instruction
        fields = "__all__"
        labels = {
            "language": "Язык",
            "type": "Тип инструкции",
            "text": "Текст инструкции",
            "external_url": "Ссылка",
            "file": "Файл",
            "is_active": "Активная инструкция",
        }
        help_texts = {
            "type": "TEXT: вводишь текст. LINK: вставляешь URL. FILE: загружаешь документ.",
            "text": "Заполняется, если тип = TEXT.",
            "external_url": "Заполняется, если тип = LINK.",
            "file": "Заполняется, если тип = FILE.",
        }
        widgets = {
            "text": forms.Textarea(
                attrs={
                    "rows": 8,
                    "placeholder": "Вставь полный текст инструкции для стажера...",
                }
            ),
            "external_url": forms.URLInput(
                attrs={"placeholder": "https://example.com/instruction"}
            ),
        }

    def clean(self):
        cleaned = super().clean()
        i_type = cleaned.get("type")
        text = (cleaned.get("text") or "").strip()
        external_url = (cleaned.get("external_url") or "").strip()
        file_obj = cleaned.get("file")

        if i_type == Instruction.InstructionType.TEXT:
            if len(text) < 10:
                self.add_error("text", "Для типа TEXT введи понятный текст (минимум 10 символов).")
            cleaned["external_url"] = None
            cleaned["file"] = None

        elif i_type == Instruction.InstructionType.LINK:
            if not external_url:
                self.add_error("external_url", "Для типа LINK укажи ссылку.")
            cleaned["text"] = ""
            cleaned["file"] = None

        elif i_type == Instruction.InstructionType.FILE:
            if not file_obj:
                self.add_error("file", "Для типа FILE прикрепи файл.")
            cleaned["text"] = ""
            cleaned["external_url"] = None

        return cleaned


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ("title", "language", "is_active", "position", "published_at")
    list_filter = ("language", "is_active")
    search_fields = ("title", "short_text", "full_text")
    ordering = ("position",)
    readonly_fields = ("id",)
    fieldsets = (
        ("Основное", {"fields": ("title", "language", "is_active", "position")}),
        ("Контент", {"fields": ("short_text", "full_text", "image")}),
        ("Публикация", {"fields": ("published_at", "created_by")}),
        ("Система", {"fields": ("id",), "classes": ("collapse",)}),
    )
    actions = None

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


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    form = FeedbackAdminForm
    list_display = (
        "type_badge",
        "author_display",
        "short_text",
        "status_badge",
        "is_read",
        "created_at",
    )
    list_filter = ("type", "status", "is_read", "is_anonymous", "created_at")
    search_fields = ("full_name", "contact", "text")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
    fieldsets = (
        ("Обращение", {"fields": ("type", "text")}),
        ("Автор", {"fields": ("is_anonymous", "full_name", "contact")}),
        ("Обработка", {"fields": ("status", "is_read")}),
        ("Система", {"fields": ("created_at",), "classes": ("collapse",)}),
    )
    actions = ("set_in_progress", "set_closed", "mark_read", "mark_unread")

    @admin.display(description="Тип")
    def type_badge(self, obj):
        colors = {
            "complaint": "#d97706",
            "suggestion": "#2563eb",
            "review": "#059669",
        }
        color = colors.get(obj.type, "#64748b")
        return format_html(
            '<span style="padding:4px 10px;border-radius:999px;background:{}22;color:{};font-weight:600;">{}</span>',
            color,
            color,
            obj.get_type_display(),
        )

    @admin.display(description="Сотрудник")
    def author_display(self, obj):
        if obj.is_anonymous:
            return "Анонимно"
        return obj.full_name or "Без имени"

    @admin.display(description="Сообщение")
    def short_text(self, obj):
        text = (obj.text or "").strip()
        if len(text) <= 80:
            return text
        return f"{text[:77]}..."

    @admin.display(description="Статус")
    def status_badge(self, obj):
        colors = {
            "new": "#2563eb",
            "in_progress": "#d97706",
            "closed": "#059669",
        }
        color = colors.get(obj.status, "#64748b")
        return format_html(
            '<span style="padding:4px 10px;border-radius:999px;background:{}22;color:{};font-weight:600;">{}</span>',
            color,
            color,
            obj.get_status_display(),
        )

    @admin.action(description="Перевести в статус: В работе")
    def set_in_progress(self, request, queryset):
        updated = queryset.update(status="in_progress", is_read=True)
        self.message_user(request, f"Обновлено обращений: {updated}")

    @admin.action(description="Перевести в статус: Закрыто")
    def set_closed(self, request, queryset):
        updated = queryset.update(status="closed", is_read=True)
        self.message_user(request, f"Обновлено обращений: {updated}")

    @admin.action(description="Отметить как прочитанные")
    def mark_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f"Отмечено как прочитанные: {updated}")

    @admin.action(description="Отметить как непрочитанные")
    def mark_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f"Отмечено как непрочитанные: {updated}")

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


@admin.register(Instruction)
class InstructionAdmin(admin.ModelAdmin):
    form = InstructionAdminForm
    list_display = ("language", "type", "is_active", "updated_at")
    list_filter = ("language", "is_active", "type")
    search_fields = ("text", "external_url")
    readonly_fields = ("preview",)

    fieldsets = (
        ("Основное", {"fields": ("language", "type", "is_active")} ),
        ("Контент", {"fields": ("text", "external_url", "file")} ),
        ("Предпросмотр", {"fields": ("preview",)}),
    )

    def preview(self, obj):
        if not obj:
            return "-"
        if obj.type == "text" and obj.text:
            return format_html("<div style='white-space:pre-wrap'>{}</div>", obj.text)
        if obj.type == "link" and obj.external_url:
            return format_html("<a href='{}' target='_blank'>{}</a>", obj.external_url, obj.external_url)
        if obj.type == "file" and obj.file:
            return format_html("<a href='{}' target='_blank'>Открыть файл</a>", obj.file.url)
        return "-"

    preview.short_description = "Предпросмотр"

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
