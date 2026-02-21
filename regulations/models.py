import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models


def validate_regulation_file_size(value):
    max_size = 20 * 1024 * 1024  # 20MB
    if value and value.size > max_size:
        raise ValidationError("Максимальный размер файла — 20MB.")


class Regulation(models.Model):
    class RegulationType(models.TextChoices):
        LINK = "link", "Ссылка"
        FILE = "file", "Файл"

    class Language(models.TextChoices):
        RU = "ru", "Русский"
        EN = "en", "English"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, verbose_name="Название")
    description = models.TextField(blank=True, verbose_name="Описание")
    type = models.CharField(
        max_length=10,
        choices=RegulationType.choices,
        verbose_name="Тип регламента",
    )
    external_url = models.URLField(blank=True, null=True, verbose_name="Ссылка")
    file = models.FileField(
        upload_to="regulations/",
        blank=True,
        null=True,
        verbose_name="Файл",
        validators=[
            FileExtensionValidator(
                allowed_extensions=["pdf", "doc", "docx", "xls", "xlsx", "txt", "ppt", "pptx"]
            ),
            validate_regulation_file_size,
        ],
    )
    position = models.PositiveIntegerField(default=0, verbose_name="Порядок")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    is_mandatory_on_day_one = models.BooleanField(
        default=False,
        verbose_name="Обязателен в первый день стажировки",
    )
    language = models.CharField(
        max_length=5,
        choices=Language.choices,
        default=Language.RU,
        verbose_name="Язык",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        ordering = ["position", "-created_at"]
        verbose_name = "Регламент"
        verbose_name_plural = "Регламенты"

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        if self.type == self.RegulationType.LINK:
            if not self.external_url:
                raise ValidationError({"external_url": "Для типа 'ссылка' поле обязательно."})
            if self.file:
                raise ValidationError({"file": "Для типа 'ссылка' файл должен быть пустым."})

        if self.type == self.RegulationType.FILE:
            if not self.file:
                raise ValidationError({"file": "Для типа 'файл' поле обязательно."})
            if self.external_url:
                raise ValidationError({"external_url": "Для типа 'файл' ссылка должна быть пустой."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class RegulationAcknowledgement(models.Model):
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="regulation_acknowledgements",
        verbose_name="Пользователь",
    )
    regulation = models.ForeignKey(
        Regulation,
        on_delete=models.CASCADE,
        related_name="acknowledgements",
        verbose_name="Регламент",
    )
    acknowledged_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата ознакомления")
    user_full_name = models.CharField(max_length=255, verbose_name="ФИО пользователя")
    regulation_title = models.CharField(max_length=255, verbose_name="Название документа")

    class Meta:
        unique_together = ("user", "regulation")
        ordering = ["-acknowledged_at"]
        verbose_name = "Ознакомление с регламентом"
        verbose_name_plural = "Ознакомления с регламентами"

    def __str__(self):
        return f"{self.user_full_name} -> {self.regulation_title}"


class RegulationReadProgress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="regulation_reads",
    )
    regulation = models.ForeignKey(
        Regulation,
        on_delete=models.CASCADE,
        related_name="read_progress",
    )
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "regulation")


class RegulationFeedback(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="regulation_feedbacks",
    )
    regulation = models.ForeignKey(
        Regulation,
        on_delete=models.CASCADE,
        related_name="feedbacks",
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class InternOnboardingRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="intern_onboarding_requests",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    note = models.TextField(blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_intern_onboarding_requests",
    )

    class Meta:
        ordering = ["-requested_at"]

