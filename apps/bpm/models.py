from django.conf import settings
from django.db import models

from accounts.models import Role


class ProcessTemplate(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class StepTemplate(models.Model):
    process_template = models.ForeignKey(
        ProcessTemplate,
        on_delete=models.CASCADE,
        related_name="steps",
    )
    name = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=1)
    role_responsible = models.CharField(max_length=32, choices=Role.Name.choices)
    requires_comment = models.BooleanField(default=False)
    sla_hours = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["order", "id"]
        unique_together = ("process_template", "order")

    def __str__(self):
        return f"{self.process_template_id}:{self.name}"


class ProcessInstance(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    template = models.ForeignKey(
        ProcessTemplate,
        on_delete=models.PROTECT,
        related_name="instances",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_process_instances",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["status"]), models.Index(fields=["created_by", "created_at"])]


class StepInstance(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"

    process_instance = models.ForeignKey(
        ProcessInstance,
        on_delete=models.CASCADE,
        related_name="steps",
    )
    step_template = models.ForeignKey(
        StepTemplate,
        on_delete=models.PROTECT,
        related_name="step_instances",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    responsible_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="step_instances_responsible",
    )
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ["step_template__order", "id"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["responsible_user", "status"]),
        ]
