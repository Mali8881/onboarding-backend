from django.contrib import admin
from django.utils.html import format_html
from .models import Instruction, LanguageSetting

from .models import News, WelcomeBlock, Feedback, Employee
from .models import NewsSliderSettings
from .models import Course, CourseEnrollment


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ("title", "language", "is_active", "position", "published_at")
    list_filter = ("language", "is_active")
    ordering = ("position",)
    actions = None


@admin.register(NewsSliderSettings)
class NewsSliderSettingsAdmin(admin.ModelAdmin):
    list_display = ("autoplay", "autoplay_delay")


@admin.register(WelcomeBlock)
class WelcomeBlockAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active")

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("type", "is_read", "created_at")
    list_filter = ("type", "is_read")
    readonly_fields = ("created_at",)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "position",
        "department",
        "telegram",
        "position_order",
        "is_active",
    )
    ordering = ("position_order",)


@admin.register(Instruction)
class InstructionAdmin(admin.ModelAdmin):
    list_display = ("language", "type", "is_active", "updated_at")
    list_filter = ("language", "is_active", "type")
    readonly_fields = ("preview",)

    fieldsets = (
        (None, {
            "fields": ("language", "type", "is_active")
        }),
        ("Контент", {
            "fields": ("text", "external_url", "file")
        }),
        ("Предпросмотр", {
            "fields": ("preview",)
        }),
    )

    def preview(self, obj):
        if not obj:
            return "—"
        if obj.type == "text" and obj.text:
            return format_html("<div style='white-space:pre-wrap'>{}</div>", obj.text)
        if obj.type == "link" and obj.external_url:
            return format_html("<a href='{}' target='_blank'>{}</a>", obj.external_url, obj.external_url)
        if obj.type == "file" and obj.file:
            return format_html("<a href='{}' target='_blank'>Открыть файл</a>", obj.file.url)
        return "—"

    preview.short_description = "Предпросмотр"


@admin.register(LanguageSetting)
class LanguageSettingAdmin(admin.ModelAdmin):
    list_display = ("code", "is_enabled")
    list_editable = ("is_enabled",)
    ordering = ("code",)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "visibility", "department", "is_active", "updated_at")
    list_filter = ("visibility", "is_active", "department")
    search_fields = ("title",)


@admin.register(CourseEnrollment)
class CourseEnrollmentAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "status", "progress_percent", "source", "updated_at")
    list_filter = ("status", "source")
    search_fields = ("user__username", "course__title")


