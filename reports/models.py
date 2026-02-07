import uuid
from django.db import models
from django.conf import settings


class Report(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        ACCEPTED = "accepted", "Accepted"
        REVISION = "revision", "Revision"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports"
    )

    onboarding_day_id = models.UUIDField(
        null=True,
        blank=True
    )

    what_done = models.TextField()
    what_next = models.TextField()
    problems = models.TextField(blank=True)
    attachment_url = models.URLField(blank=True, default="")

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    created_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Report {self.id} ({self.status})"


class ReportComment(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name="comments"
    )



    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
