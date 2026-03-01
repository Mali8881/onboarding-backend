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
        default=Status.DRAFT,  # ✅ правильный статус по умолчанию
        verbose_name="Статус"
    )

    reviewer_comment = models.TextField(
        blank=True,
        verbose_name="Комментарий проверяющего"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ---------------- БИЗНЕС-ЛОГИКА ----------------

    def can_be_sent(self) -> bool:
        """Проверка, можно ли отправить отчёт"""
        return bool(self.did.strip() and self.will_do.strip())

    def send(self):
        """Отправка отчёта стажёром"""
        if not self.can_be_sent():
            raise ValueError("Report cannot be sent: required fields are empty")

        self.status = self.Status.SENT
        self.save(update_fields=["status", "updated_at"])

        OnboardingReportLog.objects.create(
            report=self,
            action=OnboardingReportLog.Action.SENT,
            author=self.user,
        )

    def can_be_modified(self) -> bool:
        """Можно ли редактировать отчёт"""
        return self.status in [self.Status.DRAFT, self.Status.REVISION, self.Status.REJECTED]

    def set_status(self, new_status, reviewer=None, comment=None):
        """Смена статуса администратором"""

        # Проверять можно только отправленные отчёты
        if self.status != self.Status.SENT:
            raise ValueError("Проверять можно только отправленные отчёты")

        # Комментарий обязателен для REVISION и REJECTED
        if new_status in [self.Status.REVISION, self.Status.REJECTED]:
            if not comment or not comment.strip():
                raise ValueError("Комментарий обязателен для данного статуса")

        self.status = new_status

        if comment:
            self.reviewer_comment = comment.strip()

        self.save(update_fields=["status", "reviewer_comment", "updated_at"])

        OnboardingReportLog.objects.create(
            report=self,
            action=new_status,
            author=reviewer,
        )

        # Создаём уведомление пользователю
        if new_status in [self.Status.REVISION, self.Status.REJECTED]:
            ReportNotification.objects.create(
                report=self,
                text=f"Ваш отчёт был отправлен на доработку. Комментарий: {self.reviewer_comment}"
            )

    class Meta:
        unique_together = ("user", "day")
        ordering = ["day__day_number"]
        verbose_name = "Отчёт по онбордингу"
        verbose_name_plural = "Отчёты по онбордингу"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"{self.user} — День {self.day.day_number}"


# --------------------------------------------------


class OnboardingReportLog(models.Model):

    class Action(models.TextChoices):
        CREATED = "CREATED", "Создан"
        SENT = "SENT", "Отправлен"
        ACCEPTED = "ACCEPTED", "Принят"
        REVISION = "REVISION", "На доработку"
        REJECTED = "REJECTED", "Отклонён"

    report = models.ForeignKey(
        OnboardingReport,
        on_delete=models.CASCADE,
        related_name="logs"
    )

    action = models.CharField(
        max_length=20,
        choices=Action.choices
    )

    author = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


# --------------------------------------------------


class ReportNotification(models.Model):
    report = models.ForeignKey(
        OnboardingReport,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class EmployeeDailyReport(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="employee_daily_reports",
    )
    report_date = models.DateField()
    summary = models.TextField(blank=True, default="")
    started_tasks = models.TextField(blank=True, default="")
    taken_tasks = models.TextField(blank=True, default="")
    completed_tasks = models.TextField(blank=True, default="")
    blockers = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "report_date")
        ordering = ["-report_date", "-updated_at"]
