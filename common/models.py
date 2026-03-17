from django.conf import settings
from django.db import models


class Notification(models.Model):

    class Type(models.TextChoices):
        SYSTEM = "system", "Системное"
        LEARNING = "learning", "Обучение"
        INFO = "info", "Инфо"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    title = models.CharField(max_length=255)
    message = models.TextField()

    type = models.CharField(
        max_length=50,
        choices=Type.choices,
        default=Type.INFO,
    )

    event_key = models.CharField(max_length=100, blank=True, default="")
    is_pinned = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_pinned", "-created_at"]
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["is_read"]),
            models.Index(fields=["is_pinned"]),
            models.Index(fields=["type"]),
            models.Index(fields=["event_key"]),
            models.Index(fields=["expires_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.user.username})"


class NotificationTemplate(models.Model):

    code = models.CharField(max_length=100, unique=True)

    title_template = models.CharField(max_length=255)
    message_template = models.TextField()

    type = models.CharField(
        max_length=50,
        choices=Notification.Type.choices,
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Шаблон уведомления"
        verbose_name_plural = "Шаблоны уведомлений"

    def __str__(self):
        return self.code
