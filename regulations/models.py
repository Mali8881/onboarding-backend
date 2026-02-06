import uuid
from django.db import models


class Regulation(models.Model):
    class RegulationType(models.TextChoices):
        LINK = "link", "Link"
        FILE = "file", "File"

    class Language(models.TextChoices):
        RU = "ru", "Русский"
        EN = "en", "English"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    title = models.CharField(
        max_length=255,
        verbose_name="Название"
    )

    description = models.TextField(
        blank=True,
        verbose_name="Описание"
    )

    type = models.CharField(
        max_length=10,
        choices=RegulationType.choices,
        verbose_name="Тип регламента"
    )

    # content: либо ссылка, либо файл
    external_url = models.URLField(
        blank=True,
        null=True,
        verbose_name="Ссылка"
    )

    file = models.FileField(
        upload_to="regulations/",
        blank=True,
        null=True,
        verbose_name="Файл"
    )

    position = models.PositiveIntegerField(
        default=0,
        verbose_name="Порядок"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Активен"
    )

    language = models.CharField(
        max_length=5,
        choices=Language.choices,
        default=Language.RU,
        verbose_name="Язык"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position"]
        verbose_name = "Регламент"
        verbose_name_plural = "Регламенты"

    def __str__(self):
        return self.title
