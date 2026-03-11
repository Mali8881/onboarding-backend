from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Type(models.TextChoices):
        SYSTEM = "system", "System"
        LEARNING = "learning", "Learning"
        INFO = "info", "Info"

    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        CRITICAL = "critical", "Critical"

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
    code = models.CharField(max_length=100, default="generic.info")
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.INFO,
    )
    entity_type = models.CharField(max_length=100, blank=True, default="")
    entity_id = models.CharField(max_length=100, blank=True, default="")
    action_url = models.CharField(max_length=500, blank=True, default="")

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["is_read"]),
            models.Index(fields=["type"]),
            models.Index(fields=["code"]),
            models.Index(fields=["severity"]),
            models.Index(fields=["entity_type"]),
            models.Index(fields=["entity_id"]),
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
        verbose_name = "Notification template"
        verbose_name_plural = "Notification templates"

    def __str__(self):
        return self.code
