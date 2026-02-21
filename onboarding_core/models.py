from django.conf import settings
from django.utils import timezone


import uuid
from django.db import models




class OnboardingDay(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    day_number = models.PositiveIntegerField(
        unique=True,
        verbose_name="Номер дня"
    )

    title = models.CharField(
        max_length=255,
        verbose_name="Название дня"
    )

    goals = models.TextField(
        blank=True,
        verbose_name="Цели дня"
    )

    description = models.TextField(
        blank=True,
        verbose_name="Описание дня"
    )

    instructions = models.TextField(
        blank=True,
        verbose_name="Инструкции"
    )

    # дедлайн без даты — строго по ТЗ
    deadline_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Дедлайн (ЧЧ:ММ)"
    )

    # связь с регламентами
    regulations = models.ManyToManyField(
        "regulations.Regulation",
        blank=True,
        related_name="onboarding_days",
        verbose_name="Регламенты"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Активен"
    )

    position = models.PositiveIntegerField(
        default=0,
        verbose_name="Порядок отображения"
    )

    class Meta:
        ordering = ["position", "day_number"]
        verbose_name = "День онбординга"
        verbose_name_plural = "Дни онбординга"

    def __str__(self):
        return f"День {self.day_number}: {self.title}"

class OnboardingMaterial(models.Model):
    class MaterialType(models.TextChoices):
        LINK = "link", "Link"
        VIDEO = "video", "Video"
        TEXT = "text", "Text"
        IMAGE = "image", "Image"
        FILE = "file", "File"

    PRIORITY_ORDER = {
        "link": 1,
        "video": 2,
        "text": 3,
        "image": 4,
        "file": 5,
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    day = models.ForeignKey(
        OnboardingDay,
        related_name="materials",
        on_delete=models.CASCADE,
    )

    type = models.CharField(max_length=10, choices=MaterialType.choices)
    content = models.TextField()
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position"]
        unique_together = ("day", "position")
        verbose_name = "Материал онбординга"
        verbose_name_plural = "Материалы онбординга"

    def __str__(self):
        return f"{self.day} - {self.type}"

    @property
    def priority(self):
        return self.PRIORITY_ORDER.get(self.type, 99)



class OnboardingProgress(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not started"
        IN_PROGRESS = "in_progress", "In progress"
        DONE = "done", "Done"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="onboarding_progress",
    )

    day = models.ForeignKey(
        OnboardingDay,
        on_delete=models.CASCADE,
        related_name="progress",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_STARTED,
    )

    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "day")
        ordering = ["day__position", "day__day_number"]
        verbose_name = "Прогресс онбординга"
        verbose_name_plural = "Прогресс онбординга"

    def mark_done(self):
        self.status = self.Status.DONE
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at"])

    def __str__(self):
        return f"{self.user} - Day {self.day.day_number}: {self.status}"

