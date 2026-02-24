from datetime import date as dt_date
from datetime import datetime
from datetime import time as dt_time
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class WorkSchedule(models.Model):
    name = models.CharField(max_length=100)

    work_days = models.JSONField(
        help_text="Список рабочих дней недели (0=Пн ... 6=Вс)"
    )

    start_time = models.TimeField()
    end_time = models.TimeField()

    break_start = models.TimeField(null=True, blank=True)
    break_end = models.TimeField(null=True, blank=True)

    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "График работы"
        verbose_name_plural = "Графики работы"
        indexes = [
            models.Index(fields=["is_active"]),
        ]

    def clean(self):
        if not isinstance(self.work_days, list):
            raise ValidationError("work_days должен быть списком")

        for day in self.work_days:
            if not isinstance(day, int) or day < 0 or day > 6:
                raise ValidationError("work_days может содержать только числа от 0 до 6")

        if self.is_default:
            exists_default = WorkSchedule.objects.exclude(pk=self.pk).filter(is_default=True).exists()
            if exists_default:
                raise ValidationError("Может быть только один график по умолчанию")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ProductionCalendar(models.Model):
    date = models.DateField(unique=True)
    is_working_day = models.BooleanField(default=True)
    is_holiday = models.BooleanField(default=False)
    holiday_name = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = "Производственный день (РФ)"
        verbose_name_plural = "Производственный календарь (РФ)"
        ordering = ["date"]
        indexes = [
            models.Index(fields=["date"]),
        ]

    def clean(self):
        if self.is_holiday and self.is_working_day:
            raise ValidationError("День не может быть одновременно рабочим и праздничным")

    def __str__(self):
        return f"{self.date}"


class UserWorkSchedule(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="work_schedule",
    )

    schedule = models.ForeignKey(
        WorkSchedule,
        on_delete=models.CASCADE,
        related_name="users",
    )

    approved = models.BooleanField(default=True)
    requested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "График пользователя"
        verbose_name_plural = "Графики пользователей"
        indexes = [
            models.Index(fields=["approved"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.schedule}"


class WeeklyWorkPlan(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CLARIFICATION_REQUESTED = "clarification_requested", "Clarification requested"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="weekly_work_plans",
    )
    week_start = models.DateField(
        help_text="Week start date (Monday).",
    )
    days = models.JSONField(default=list)
    office_hours = models.PositiveSmallIntegerField(default=24)
    online_hours = models.PositiveSmallIntegerField(default=0)
    online_reason = models.TextField(blank=True)
    employee_comment = models.TextField(blank=True)

    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.PENDING,
    )
    admin_comment = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_weekly_work_plans",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Weekly work plan"
        verbose_name_plural = "Weekly work plans"
        constraints = [
            models.UniqueConstraint(fields=["user", "week_start"], name="unique_user_weekly_plan"),
        ]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["week_start"]),
            models.Index(fields=["user", "week_start"]),
        ]

    def clean(self):
        if self.week_start and self.week_start.weekday() != 0:
            raise ValidationError({"week_start": "week_start must be a Monday."})

        if not isinstance(self.days, list):
            raise ValidationError({"days": "days must be a list of shifts."})
        if len(self.days) != 7:
            raise ValidationError({"days": "Exactly 7 shifts are required (Monday..Sunday)."})

        allowed_keys = {"date", "start_time", "end_time", "mode", "comment"}
        total_office = 0
        total_online = 0
        seen_dates = set()

        for idx, raw in enumerate(self.days, start=1):
            if not isinstance(raw, dict):
                raise ValidationError({"days": f"Item #{idx} must be an object."})

            unknown = set(raw.keys()) - allowed_keys
            if unknown:
                raise ValidationError({"days": f"Unknown fields in item #{idx}: {sorted(unknown)}"})

            day_date = self._parse_date(raw.get("date"), idx)
            mode = raw.get("mode")

            if mode not in {"office", "online", "day_off"}:
                raise ValidationError({"days": f"Item #{idx}: mode must be 'office', 'online' or 'day_off'."})

            if self.week_start:
                week_end = self.week_start + timedelta(days=6)
                if day_date < self.week_start or day_date > week_end:
                    raise ValidationError({"days": f"Item #{idx}: date must be inside selected week."})
                expected = {self.week_start + timedelta(days=i) for i in range(7)}
                if day_date not in expected:
                    raise ValidationError({"days": f"Item #{idx}: date must be inside Monday..Sunday."})

            if day_date in seen_dates:
                raise ValidationError({"days": f"Item #{idx}: duplicate date {day_date.isoformat()}."})
            seen_dates.add(day_date)

            if mode == "day_off":
                if raw.get("start_time") is not None or raw.get("end_time") is not None:
                    raise ValidationError({"days": f"Item #{idx}: day_off must not contain start/end time."})
                continue

            start_time = self._parse_time(raw.get("start_time"), idx, "start_time")
            end_time = self._parse_time(raw.get("end_time"), idx, "end_time")

            start_dt = datetime.combine(day_date, start_time)
            end_dt = datetime.combine(day_date, end_time)
            if end_dt <= start_dt:
                raise ValidationError({"days": f"Item #{idx}: end_time must be after start_time."})

            min_hour, max_hour = self._day_hour_limits(day_date)
            if start_time.hour < min_hour or end_time.hour > max_hour:
                raise ValidationError(
                    {"days": f"Item #{idx}: allowed time is {min_hour:02d}:00-{max_hour:02d}:00 for this day."}
                )

            duration_hours = (end_dt - start_dt).seconds // 3600
            if duration_hours <= 0:
                raise ValidationError({"days": f"Item #{idx}: shift duration must be at least 1 hour."})

            if mode == "office":
                total_office += duration_hours
            else:
                total_online += duration_hours

        if self.week_start:
            expected = {self.week_start + timedelta(days=i) for i in range(7)}
            missing = sorted(d.isoformat() for d in (expected - seen_dates))
            if missing:
                raise ValidationError({"days": f"Missing shifts for dates: {', '.join(missing)}"})

        # Keep aggregate totals synchronized with day-by-day payload.
        self.office_hours = total_office
        self.online_hours = total_online

        needs_reason = self.office_hours < 24 or self.online_hours > 16
        if needs_reason and not (self.online_reason or "").strip():
            raise ValidationError(
                {"online_reason": "Reason is required when office hours are below 24 and/or online hours exceed 16."}
            )

    @staticmethod
    def _parse_date(value, idx: int):
        if isinstance(value, dt_date):
            return value
        if isinstance(value, str):
            try:
                return dt_date.fromisoformat(value)
            except ValueError as exc:
                raise ValidationError({"days": f"Item #{idx}: invalid date format, use YYYY-MM-DD."}) from exc
        raise ValidationError({"days": f"Item #{idx}: date is required."})

    @staticmethod
    def _parse_time(value, idx: int, field_name: str):
        if isinstance(value, dt_time):
            parsed = value
        elif isinstance(value, str):
            try:
                parsed = dt_time.fromisoformat(value)
            except ValueError as exc:
                raise ValidationError({"days": f"Item #{idx}: invalid {field_name} format, use HH:MM."}) from exc
        else:
            raise ValidationError({"days": f"Item #{idx}: {field_name} is required."})

        if parsed.minute != 0 or parsed.second != 0 or parsed.microsecond != 0:
            raise ValidationError({"days": f"Item #{idx}: {field_name} must be set in full hours (HH:00)."})
        return parsed

    @staticmethod
    def _day_hour_limits(day_date: dt_date):
        if day_date.weekday() < 5:
            return 9, 21
        return 11, 19

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} - {self.week_start} ({self.status})"
