import uuid
from django.db import models

from accounts.models import User
from onboarding_core.models import OnboardingDay


class OnboardingReport(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Черновик"
        SENT = "SENT", "Отправлен"
        ACCEPTED = "ACCEPTED", "Принят"
        REVISION = "REVISION", "На доработку"
        REJECTED = "REJECTED", "Отклонён"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="onboarding_reports",
        verbose_name="Стажёр"
    )

    day = models.ForeignKey(
        OnboardingDay,
        on_delete=models.CASCADE,
        related_name="reports",
        verbose_name="День онбординга"
    )

    did = models.TextField(verbose_name="Что сделал")
    will_do = models.TextField(verbose_name="Что буду делать")
    problems = models.TextField(blank=True, verbose_name="Проблемы")

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SENT,
        verbose_name="Статус"
    )

    reviewer_comment = models.TextField(
        blank=True,
        verbose_name="Комментарий проверяющего"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "day")
        ordering = ["day__day_number"]
        verbose_name = "Отчёт по онбордингу"
        verbose_name_plural = "Отчёты по онбордингу"

    def __str__(self):
        return f"{self.user} — День {self.day.day_number}"

class OnboardingReportLog(models.Model):
    report = models.ForeignKey(
        OnboardingReport,
        on_delete=models.CASCADE,
        related_name="logs"
    )
    action = models.CharField(max_length=20)
    author = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)

class ReportNotification(models.Model):
    report = models.ForeignKey(
        OnboardingReport,
        on_delete=models.CASCADE,
        related_name="notifications"
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
