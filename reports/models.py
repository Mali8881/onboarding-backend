import uuid
from django.db import models
from django.conf import settings


class OnboardingReport(models.Model):
    """
    Ежедневный отчёт стажёра
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        REVISION = "revision", "Revision"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports",
    )

    day = models.ForeignKey(
        "onboarding_core.OnboardingDay",
        on_delete=models.CASCADE,
        related_name="reports",
    )

    # -------- поля отчёта --------
    did = models.TextField(blank=True)
    will_do = models.TextField(blank=True)
    problems = models.TextField(blank=True)

    attachment = models.TextField(blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    submitted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "day")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} | Day {self.day.day_number} | {self.status}"


class OnboardingReportComment(models.Model):
    """
    Комментарий администратора
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    report = models.ForeignKey(
        OnboardingReport,
        on_delete=models.CASCADE,
        related_name="comments",
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="report_comments",
    )

    text = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.author} on {self.report_id}"


class OnboardingReportLog(models.Model):
    """
    Логирование всех действий с отчётом
    """

    class Action(models.TextChoices):
        CREATED = "created", "Created"
        SUBMITTED = "submitted", "Submitted"
        STATUS_CHANGED = "status_changed", "Status changed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    report = models.ForeignKey(
        OnboardingReport,
        on_delete=models.CASCADE,
        related_name="logs",
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="report_logs",
    )

    action = models.CharField(max_length=30, choices=Action.choices)

    from_status = models.CharField(max_length=20, blank=True, null=True)
    to_status = models.CharField(max_length=20, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.report_id}: {self.action}"

class ReportNotification(models.Model):
    class Type(models.TextChoices):
        REPORT_SUBMITTED = "report_submitted", "Report submitted"
        REPORT_APPROVED = "report_approved", "Report approved"
        REPORT_REVISION = "report_revision", "Report revision"
        REPORT_REJECTED = "report_rejected", "Report rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="report_notifications",
    )

    report = models.ForeignKey(
        "reports.OnboardingReport",
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    type = models.CharField(max_length=50, choices=Type.choices)
    message = models.CharField(max_length=255)

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} — {self.type}"
