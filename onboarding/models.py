"""
Модели для системы онбординга стажёров
"""
import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from django.core.exceptions import ValidationError


class OnboardingDay(models.Model):
    """
    Модель для представления одного дня стажировки
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )

    day_number = models.PositiveIntegerField(
        verbose_name='Номер дня',
        validators=[MinValueValidator(1)],
        unique=True,
        help_text='Порядковый номер дня стажировки'
    )

    title = models.CharField(
        max_length=200,
        verbose_name='Название дня',
        help_text='Например: "Знакомство с компанией"'
    )

    description = models.TextField(
        verbose_name='Описание целей дня',
        help_text='Подробное описание задач и целей на день',
        blank=True
    )

    instructions = models.TextField(
        verbose_name='Инструкции',
        help_text='Текстовые инструкции для стажёра',
        blank=True
    )

    deadline_time = models.TimeField(
        verbose_name='Дедлайн (время)',
        help_text='Время дедлайна в формате ЧЧ:ММ',
        default='18:00'
    )

    is_active = models.BooleanField(
        verbose_name='Активен',
        default=True,
        help_text='Отображается ли день в интерфейсе стажёра'
    )

    position = models.PositiveIntegerField(
        verbose_name='Порядок отображения',
        default=0,
        help_text='Порядковый номер для сортировки'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'День онбординга'
        verbose_name_plural = 'Дни онбординга'
        ordering = ['position', 'day_number']
        indexes = [
            models.Index(fields=['day_number']),
            models.Index(fields=['position']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"День {self.day_number}. {self.title}"

    def clean(self):
        """Валидация модели"""
        super().clean()

        # Проверка на количество материалов (максимум 10)
        if self.pk:
            materials_count = self.materials.count()
            if materials_count > 10:
                raise ValidationError(
                    f'Превышен лимит медиа-элементов. Максимум: 10, текущее количество: {materials_count}'
                )

    def get_materials_count(self):
        """Получить количество материалов для этого дня"""
        return self.materials.count()

    def get_active_materials(self):
        """Получить все активные материалы в правильном порядке"""
        return self.materials.filter(is_active=True).order_by('position')


class OnboardingMaterial(models.Model):
    """
    Модель для медиа-материалов дня онбординга
    """

    MATERIAL_TYPES = [
        ('text', 'Текст'),
        ('link', 'Ссылка'),
        ('video', 'Видео'),
        ('file', 'Файл'),
        ('image', 'Изображение'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )

    onboarding_day = models.ForeignKey(
        OnboardingDay,
        on_delete=models.CASCADE,
        related_name='materials',
        verbose_name='День онбординга'
    )

    type = models.CharField(
        max_length=20,
        choices=MATERIAL_TYPES,
        verbose_name='Тип материала',
        help_text='Выберите тип контента'
    )

    title = models.CharField(
        max_length=200,
        verbose_name='Заголовок',
        help_text='Название материала',
        blank=True
    )

    content = models.TextField(
        verbose_name='Контент',
        help_text='Текст, ссылка или описание',
        blank=True
    )

    file = models.FileField(
        upload_to='onboarding/materials/%Y/%m/',
        verbose_name='Файл',
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'jpg', 'jpeg', 'png',
                                    'gif', 'mp4', 'avi']
            )
        ],
        help_text='Загрузите файл (для типа "Файл" или "Изображение")'
    )

    video_url = models.URLField(
        verbose_name='URL видео',
        blank=True,
        null=True,
        help_text='Ссылка на YouTube, Vimeo или другой видеохостинг'
    )

    position = models.PositiveIntegerField(
        verbose_name='Порядок отображения',
        default=0,
        help_text='Порядковый номер материала в рамках дня'
    )

    is_active = models.BooleanField(
        verbose_name='Активен',
        default=True,
        help_text='Отображается ли материал'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Материал онбординга'
        verbose_name_plural = 'Материалы онбординга'
        ordering = ['position', 'created_at']
        indexes = [
            models.Index(fields=['onboarding_day', 'position']),
            models.Index(fields=['type']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.get_type_display()} - {self.title or 'Без названия'}"

    def clean(self):
        """Валидация модели"""
        super().clean()

        # Проверка на превышение лимита материалов (10 на день)
        if self.onboarding_day_id:
            existing_materials = OnboardingMaterial.objects.filter(
                onboarding_day=self.onboarding_day
            ).exclude(pk=self.pk).count()

            if existing_materials >= 10:
                raise ValidationError(
                    'Нельзя добавить больше 10 материалов на один день онбординга'
                )

        # Валидация в зависимости от типа
        if self.type == 'file' and not self.file:
            raise ValidationError({'file': 'Для типа "Файл" необходимо загрузить файл'})

        if self.type == 'image' and not self.file:
            raise ValidationError({'file': 'Для типа "Изображение" необходимо загрузить файл'})

        if self.type == 'video' and not self.video_url and not self.file:
            raise ValidationError({'video_url': 'Для типа "Видео" необходимо указать URL или загрузить файл'})

        if self.type == 'link' and not self.content:
            raise ValidationError({'content': 'Для типа "Ссылка" необходимо указать URL в поле "Контент"'})

        if self.type == 'text' and not self.content:
            raise ValidationError({'content': 'Для типа "Текст" необходимо заполнить поле "Контент"'})

    def save(self, *args, **kwargs):
        """Переопределение сохранения для валидации"""
        self.full_clean()
        super().save(*args, **kwargs)

    def get_display_content(self):
        """Получить контент для отображения в зависимости от типа"""
        if self.type == 'text':
            return self.content
        elif self.type == 'link':
            return self.content
        elif self.type == 'video':
            return self.video_url or self.file.url if self.file else None
        elif self.type in ['file', 'image']:
            return self.file.url if self.file else None
        return None

    def is_youtube_video(self):
        """Проверка, является ли видео YouTube"""
        if self.video_url:
            return 'youtube.com' in self.video_url or 'youtu.be' in self.video_url
        return False

    def is_vimeo_video(self):
        """Проверка, является ли видео Vimeo"""
        if self.video_url:
            return 'vimeo.com' in self.video_url
        return False

    def get_youtube_embed_url(self):
        """Получить embed URL для YouTube"""
        if not self.is_youtube_video():
            return None

        if 'youtu.be/' in self.video_url:
            video_id = self.video_url.split('youtu.be/')[-1].split('?')[0]
        elif 'watch?v=' in self.video_url:
            video_id = self.video_url.split('watch?v=')[-1].split('&')[0]
        else:
            return None

        return f"https://www.youtube.com/embed/{video_id}"

    def get_vimeo_embed_url(self):
        """Получить embed URL для Vimeo"""
        if not self.is_vimeo_video():
            return None

        video_id = self.video_url.split('vimeo.com/')[-1].split('?')[0]
        return f"https://player.vimeo.com/video/{video_id}"


class InternReport(models.Model):
    """
    Модель для отчётов стажёров (стендапов)
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )

    onboarding_day = models.ForeignKey(
        OnboardingDay,
        on_delete=models.CASCADE,
        related_name='reports',
        verbose_name='День онбординга'
    )

    # Здесь должна быть связь с моделью User (стажёр)
    # user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='intern_reports')

    report_text = models.TextField(
        verbose_name='Текст отчёта',
        help_text='Стендап стажёра за день'
    )

    submitted_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата и время отправки'
    )

    is_late = models.BooleanField(
        verbose_name='Сдан с опозданием',
        default=False,
        help_text='Был ли отчёт отправлен после дедлайна'
    )

    reviewed = models.BooleanField(
        verbose_name='Проверен',
        default=False
    )

    review_comment = models.TextField(
        verbose_name='Комментарий проверяющего',
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = 'Отчёт стажёра'
        verbose_name_plural = 'Отчёты стажёров'
        ordering = ['-submitted_at']
        # Один стажёр может отправить только один отчёт на день
        # unique_together = [['user', 'onboarding_day']]

    def __str__(self):
        return f"Отчёт за День {self.onboarding_day.day_number}"