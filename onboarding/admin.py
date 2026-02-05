"""
Настройка административной панели для онбординга
"""
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import OnboardingDay, OnboardingMaterial, InternReport


class OnboardingMaterialInline(admin.TabularInline):
    """
    Встроенное редактирование материалов прямо на странице дня
    """
    model = OnboardingMaterial
    extra = 1
    max_num = 10  # Ограничение на 10 материалов
    fields = ['type', 'title', 'content', 'file', 'video_url', 'position', 'is_active']
    ordering = ['position']


@admin.register(OnboardingDay)
class OnboardingDayAdmin(admin.ModelAdmin):
    """
    Административная панель для управления днями онбординга
    """
    list_display = [
        'day_number',
        'title',
        'deadline_time',
        'materials_count',
        'is_active',
        'position',
        'created_at'
    ]

    list_filter = [
        'is_active',
        'created_at',
        'deadline_time'
    ]

    search_fields = [
        'title',
        'description',
        'instructions',
        'day_number'
    ]

    list_editable = [
        'is_active',
        'position'
    ]

    ordering = ['position', 'day_number']

    fieldsets = (
        ('Основная информация', {
            'fields': ('day_number', 'title', 'position', 'is_active')
        }),
        ('Контент дня', {
            'fields': ('description', 'instructions', 'deadline_time'),
            'description': 'Описание целей дня и текстовые инструкции для стажёра'
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', 'updated_at']

    inlines = [OnboardingMaterialInline]

    def materials_count(self, obj):
        """Отображение количества материалов"""
        count = obj.get_materials_count()
        if count >= 10:
            return format_html(
                '<span style="color: red; font-weight: bold;">{}/10 (лимит)</span>',
                count
            )
        elif count >= 7:
            return format_html(
                '<span style="color: orange;">{}/10</span>',
                count
            )
        else:
            return format_html('{}/10', count)

    materials_count.short_description = 'Материалы'

    def get_queryset(self, request):
        """Оптимизация запросов с подсчётом материалов"""
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            _materials_count=Count('materials', distinct=True)
        )
        return queryset

    class Media:
        css = {
            'all': ('admin/css/custom_onboarding.css',)
        }


@admin.register(OnboardingMaterial)
class OnboardingMaterialAdmin(admin.ModelAdmin):
    """
    Административная панель для управления материалами онбординга
    """
    list_display = [
        'title',
        'type',
        'onboarding_day',
        'position',
        'is_active',
        'preview',
        'created_at'
    ]

    list_filter = [
        'type',
        'is_active',
        'onboarding_day__day_number',
        'created_at'
    ]

    search_fields = [
        'title',
        'content',
        'onboarding_day__title'
    ]

    list_editable = [
        'position',
        'is_active'
    ]

    ordering = ['onboarding_day__position', 'position']

    fieldsets = (
        ('Основная информация', {
            'fields': ('onboarding_day', 'type', 'title', 'position', 'is_active')
        }),
        ('Контент', {
            'fields': ('content', 'file', 'video_url'),
            'description': 'Заполните поля в зависимости от типа материала'
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', 'updated_at']

    def preview(self, obj):
        """Предварительный просмотр материала"""
        if obj.type == 'image' and obj.file:
            return format_html(
                '<img src="{}" style="max-width: 100px; max-height: 100px;" />',
                obj.file.url
            )
        elif obj.type == 'link':
            return format_html(
                '<a href="{}" target="_blank">🔗 Открыть</a>',
                obj.content
            )
        elif obj.type == 'video':
            if obj.is_youtube_video():
                return '▶️ YouTube'
            elif obj.is_vimeo_video():
                return '▶️ Vimeo'
            return '▶️ Видео'
        elif obj.type == 'file' and obj.file:
            return format_html(
                '<a href="{}" target="_blank">📄 Скачать</a>',
                obj.file.url
            )
        elif obj.type == 'text':
            preview_text = obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
            return preview_text
        return '-'

    preview.short_description = 'Превью'

    def save_model(self, request, obj, form, change):
        """Проверка лимита материалов перед сохранением"""
        try:
            super().save_model(request, obj, form, change)
        except Exception as e:
            self.message_user(request, f'Ошибка: {str(e)}', level='error')


@admin.register(InternReport)
class InternReportAdmin(admin.ModelAdmin):
    """
    Административная панель для просмотра отчётов стажёров
    """
    list_display = [
        'onboarding_day',
        # 'user',  # Раскомментировать когда будет модель User
        'submitted_at',
        'is_late',
        'reviewed',
        'preview_report'
    ]

    list_filter = [
        'is_late',
        'reviewed',
        'submitted_at',
        'onboarding_day__day_number'
    ]

    search_fields = [
        'report_text',
        # 'user__username',  # Раскомментировать когда будет модель User
        'onboarding_day__title'
    ]

    list_editable = ['reviewed']

    readonly_fields = ['submitted_at', 'is_late']

    fieldsets = (
        ('Информация об отчёте', {
            'fields': ('onboarding_day', 'submitted_at', 'is_late')
        }),
        ('Содержимое', {
            'fields': ('report_text',)
        }),
        ('Проверка', {
            'fields': ('reviewed', 'review_comment')
        }),
    )

    ordering = ['-submitted_at']

    def preview_report(self, obj):
        """Превью текста отчёта"""
        preview = obj.report_text[:100] + '...' if len(obj.report_text) > 100 else obj.report_text
        return preview

    preview_report.short_description = 'Превью отчёта'

    def has_add_permission(self, request):
        """Отчёты создаются только через интерфейс стажёра"""
        return False