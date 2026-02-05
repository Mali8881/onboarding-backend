import uuid
from django.db import models


class OnboardingDay(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    day_number = models.PositiveIntegerField(unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    deadline_time = models.TimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "day_number"]

    def __str__(self):
        return f"Day {self.day_number}: {self.title}"


class OnboardingMaterial(models.Model):
    class MaterialType(models.TextChoices):
        TEXT = "text", "Text"
        LINK = "link", "Link"
        VIDEO = "video", "Video"
        FILE = "file", "File"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    onboarding_day = models.ForeignKey(
        OnboardingDay,
        related_name="materials",
        on_delete=models.CASCADE,
    )
    type = models.CharField(
        max_length=10,
        choices=MaterialType.choices,
    )
    content = models.TextField()
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position"]

    def __str__(self):
        return f"{self.type} for {self.onboarding_day}"

