import uuid
import re
from django.db import models
from django.conf import settings
from django.utils.html import strip_tags
from ckeditor_uploader.fields import RichTextUploadingField
from jsonschema.exceptions import ValidationError

from django.utils import timezone

# 🔹 НАСТРОЙКИ СЛАЙДЕРА (вынесено вверх для логики)
class NewsSliderSettings(models.Model):
    autoplay = models.BooleanField(
        default=True,
        verbose_name="Автопрокрутка"
    )
    autoplay_delay = models.PositiveIntegerField(
        default=5000,
        verbose_name="Задержка (мс)",
        help_text="Задержка в миллисекундах"
    )

    class Meta:
        verbose_name = "Настройки слайдера новостей"
        verbose_name_plural = "Настройки слайдера новостей"

    def __str__(self):
        return f"Настройки слайдера (Авто: {self.autoplay})"


# 🔹 НОВОСТИ
class News(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    language = models.CharField(
        "Язык",
        max_length=2,
        choices=[("ru", "RU"), ("en", "EN"), ("kg", "KG")],
        default="ru"
    )

    title = models.CharField("Заголовок", max_length=255)
    short_text = models.CharField("Краткое описание", max_length=255, blank=True)
    full_text = RichTextUploadingField("Полный текст")

    image = models.ImageField(
        "Изображение",
        upload_to="news/",
        null=True,
        blank=True
    )

    published_at = models.DateTimeField("Дата публикации")
    is_active = models.BooleanField("Активна", default=True)
    position = models.PositiveIntegerField("Порядок", default=0)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Автор"
    )

    class Meta:
        ordering = ["position", "-published_at"]
        verbose_name = "Новость"
        verbose_name_plural = "Новости"

    def __str__(self):
        return self.title

    def get_short_text(self):
        """Возвращает short_text или первое предложение из full_text без тегов."""
        if self.short_text:
            return self.short_text

        # Очищаем HTML и берем первое предложение
        clean_text = strip_tags(self.full_text)
        sentences = re.split(r'(?<=[.!?])\s+', clean_text)
        return sentences[0] if sentences else ""


# 🔹 ИНСТРУКЦИИ
class Instruction(models.Model):
    class InstructionType(models.TextChoices):
        TEXT = "text", "Текст"
        LINK = "link", "Ссылка"
        FILE = "file", "Файл"

    class Language(models.TextChoices):
        RU = "ru", "Русский"
        EN = "en", "English"
        KG = "kg", "Кыргызча"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    language = models.CharField(
        max_length=5,
        choices=Language.choices,
        default=Language.RU,
        verbose_name="Язык"
    )
    type = models.CharField(
        max_length=10,
        choices=InstructionType.choices,
        verbose_name="Тип инструкции"
    )
    text = models.TextField(blank=True, verbose_name="Текст инструкции")
    external_url = models.URLField(blank=True, null=True, verbose_name="Ссылка")
    file = models.FileField(upload_to="instructions/", blank=True, null=True, verbose_name="Файл")
    is_active = models.BooleanField(default=False, verbose_name="Актуальная инструкция")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("language", "is_active")  # Опционально, зависит от бизнес-логики
        verbose_name = "Инструкция"
        verbose_name_plural = "Инструкции"

    def __str__(self):
        return f"Инструкция {self.type} ({self.get_language_display()})"

    def save(self, *args, **kwargs):
        if self.is_active:
            # Деактивируем другие активные инструкции ТОЛЬКО для этого языка
            Instruction.objects.filter(
                language=self.language,
                is_active=True
            ).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)


# 🔹 ПРИВЕТСТВЕННЫЙ БЛОК
class WelcomeBlock(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    title = models.CharField(max_length=255)
    text = models.TextField()
    language = models.CharField(
        max_length=10,
        default="ru"
    )

    instruction = models.OneToOneField(
        Instruction,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    order = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        verbose_name = "Приветственный блок"
        verbose_name_plural = "Приветственные блоки"
        constraints = [
            models.UniqueConstraint(
                fields=['order', 'language'],
                name='unique_order_per_language'
            )
        ]

    def clean(self):
        existing = WelcomeBlock.objects.filter(
            language=self.language,
            is_active=True
        ).exclude(pk=self.pk).first()

        if existing and existing.is_active:
            raise ValidationError("Активный блок уже существует для этого языка")


# 🔹 ОБРАТНАЯ СВЯЗЬ
class Feedback(models.Model):

    TYPE_CHOICES = (
        ('complaint', 'Жалоба'),
        ('suggestion', 'Предложение'),
        ('review', 'Отзыв'),
    )

    STATUS_CHOICES = (
        ('new', 'Новое'),
        ('in_progress', 'В работе'),
        ('closed', 'Закрыто'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    is_anonymous = models.BooleanField(default=True)

    full_name = models.CharField(max_length=255, blank=True, null=True)
    contact = models.CharField(max_length=100, blank=True, null=True)

    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    text = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new'
    )

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)

    def clean(self):
        # текст обязателен всегда
        if not self.text or not self.text.strip():
            raise ValidationError("Текст обращения обязателен")

        # если НЕ анонимное → обязательны ФИО и контакт
        if not self.is_anonymous:
            if not self.full_name:
                raise ValidationError("ФИО обязательно для неанонимного обращения")
            if not self.contact:
                raise ValidationError("Контакт обязателен для неанонимного обращения")

        # если анонимное → запрещаем ФИО и контакт
        if self.is_anonymous:
            self.full_name = None
            self.contact = None

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Обращение"
        verbose_name_plural = "Обращения"
# 🔹 СОТРУДНИКИ
class Employee(models.Model):
    full_name = models.CharField("ФИО", max_length=255)
    position = models.CharField("Должность", max_length=255)
    department = models.CharField("Подразделение", max_length=255, blank=True)
    telegram = models.CharField(
        "Telegram",
        max_length=50,
        blank=True,
        help_text="Например: @username"
    )
    photo = models.ImageField(upload_to="employees/", null=True, blank=True)
    position_order = models.PositiveIntegerField("Порядок", default=0)
    is_active = models.BooleanField("Активен", default=True)
    is_management = models.BooleanField(
        "Руководство",
        default=False
    )

    class Meta:
        ordering = ["position_order", "full_name"]
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"

    def __str__(self):
        return self.full_name


# 🔹 ЯЗЫКИ ИНТЕРФЕЙСА
class LanguageSetting(models.Model):
    class Language(models.TextChoices):
        RU = "ru", "Русский"
        EN = "en", "English"
        KG = "kg", "Кыргызча"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(
        max_length=5,
        choices=Language.choices,
        unique=True,
        verbose_name="Язык"
    )
    is_enabled = models.BooleanField(default=True, verbose_name="Включён")

    class Meta:
        verbose_name = "Язык интерфейса"
        verbose_name_plural = "Языки интерфейса"

    def __str__(self):
        return f"{self.get_code_display()} ({'ON' if self.is_enabled else 'OFF'})"
