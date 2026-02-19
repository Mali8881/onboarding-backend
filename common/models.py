from django.db import models
from django.conf import settings


class Notification(models.Model):

    class Type(models.TextChoices):
        SYSTEM = "system", "System"
        LEARNING = "learning", "Learning"
        INFO = "info", "Info"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    title = models.CharField(max_length=255)
    message = models.TextField()

    type = models.CharField(
        max_length=50,
        choices=Type.choices,
        default=Type.INFO
    )

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["is_read"]),
            models.Index(fields=["type"]),
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
        choices=Notification.Type.choices
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code
