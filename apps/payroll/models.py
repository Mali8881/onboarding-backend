from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class PayrollCompensation(models.Model):
    class PayType(models.TextChoices):
        HOURLY = "hourly", "Hourly"
        MINUTE = "minute", "Minute"
        FIXED_SALARY = "fixed_salary", "Fixed salary"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payroll_compensation",
    )
    pay_type = models.CharField(max_length=20, choices=PayType.choices, default=PayType.HOURLY)
    hourly_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    minute_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    fixed_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["pay_type"]),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.pay_type}"


class HourlyRateHistory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hourly_rate_history",
    )
    rate = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    start_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date", "-id"]
        indexes = [
            models.Index(fields=["user", "start_date"]),
            models.Index(fields=["start_date"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["user", "start_date"], name="payroll_unique_rate_user_start_date"),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.rate}@{self.start_date}"


class PayrollRecord(models.Model):
    class Status(models.TextChoices):
        CALCULATED = "calculated", "Calculated"
        PAID = "paid", "Paid"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payroll_records",
    )
    month = models.DateField(help_text="First day of payroll month")
    total_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    total_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    bonus = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CALCULATED)
    calculated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["month", "user_id"]
        indexes = [
            models.Index(fields=["month"]),
            models.Index(fields=["status"]),
            models.Index(fields=["user", "month"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["user", "month"], name="payroll_unique_record_user_month"),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.month}:{self.total_salary}"
