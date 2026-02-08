import uuid
from django.db import models
from django.conf import settings


class SystemLog(models.Model):
    class Level(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        ERROR = "error", "Error"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="system_logs",
    )

    action = models.CharField(max_length=255)

    level = models.CharField(
        max_length=20,
        choices=Level.choices,
        default=Level.INFO,
    )

    metadata = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Системный лог"
        verbose_name_plural = "Системные логи"

    def __str__(self):
        return f"{self.created_at} | {self.action}"
