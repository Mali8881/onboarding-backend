import ipaddress

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class WorkCalendarDay(models.Model):
    date = models.DateField(unique=True)
    is_working_day = models.BooleanField(default=True)
    is_holiday = models.BooleanField(default=False)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["date"]
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["is_working_day"]),
            models.Index(fields=["is_holiday"]),
        ]

    def clean(self):
        if self.is_holiday and self.is_working_day:
            raise ValidationError("Day cannot be both holiday and working day.")

    def __str__(self):
        return str(self.date)


class OfficeNetwork(models.Model):
    name = models.CharField(max_length=150)
    cidr = models.CharField(max_length=64, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["cidr"]),
        ]

    def clean(self):
        try:
            ipaddress.ip_network(self.cidr, strict=False)
        except ValueError as exc:
            raise ValidationError({"cidr": "Invalid network. Use CIDR format, e.g. 203.0.113.0/24"}) from exc

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.cidr})"


class AttendanceMark(models.Model):
    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        REMOTE = "remote", "Remote"
        VACATION = "vacation", "Vacation"
        SICK = "sick", "Sick"
        ABSENT = "absent", "Absent"
        BUSINESS_TRIP = "business_trip", "Business trip"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="attendance_marks",
    )
    date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices)
    planned_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    actual_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    comment = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_marks_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "date")
        ordering = ["-date", "user_id"]
        indexes = [
            models.Index(fields=["user", "date"]),
            models.Index(fields=["date"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.user_id} {self.date} {self.status}"


class AttendanceSession(models.Model):
    class Result(models.TextChoices):
        IN_OFFICE = "IN_OFFICE", "In office"
        OUTSIDE_GEOFENCE = "OUTSIDE_GEOFENCE", "Outside geofence"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="attendance_sessions",
    )
    checked_at = models.DateTimeField(auto_now_add=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    accuracy_m = models.FloatField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    distance_m = models.FloatField()
    office_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    office_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    radius_m = models.PositiveIntegerField()
    result = models.CharField(max_length=32, choices=Result.choices)
    attendance_mark = models.ForeignKey(
        "AttendanceMark",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessions",
    )

    class Meta:
        ordering = ["-checked_at"]
        indexes = [
            models.Index(fields=["user", "checked_at"]),
            models.Index(fields=["result"]),
            models.Index(fields=["checked_at"]),
        ]

    def __str__(self):
        return f"{self.user_id} {self.checked_at} {self.result}"
