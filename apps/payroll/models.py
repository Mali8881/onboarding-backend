from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class SalaryProfile(models.Model):
    class EmploymentType(models.TextChoices):
        FIXED = "fixed", "Fixed"
        DAILY = "daily", "Daily"
        HOURLY = "hourly", "Hourly"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="salary_profile",
    )
    base_salary = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    employment_type = models.CharField(max_length=20, choices=EmploymentType.choices)
    currency = models.CharField(max_length=8, default="RUB")
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["employment_type"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.employment_type}"


class PayrollPeriod(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        LOCKED = "locked", "Locked"
        PAID = "paid", "Paid"

    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("year", "month")
        ordering = ["-year", "-month"]
        indexes = [
            models.Index(fields=["year", "month"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.year}-{self.month:02d}:{self.status}"


class PayrollEntry(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payroll_entries",
    )
    period = models.ForeignKey(
        PayrollPeriod,
        on_delete=models.CASCADE,
        related_name="entries",
    )
    planned_days = models.PositiveIntegerField(default=0)
    worked_days = models.PositiveIntegerField(default=0)
    advances = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    salary_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "period")
        ordering = ["user_id"]
        indexes = [
            models.Index(fields=["user", "period"]),
            models.Index(fields=["period"]),
        ]

    def __str__(self):
        return f"{self.period_id}:{self.user_id}"

