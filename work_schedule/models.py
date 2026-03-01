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

        allowed_keys = {"date", "start_time", "end_time", "mode", "comment", "breaks", "lunch_start", "lunch_end"}
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
            breaks = raw.get("breaks") or []
            lunch_start_raw = raw.get("lunch_start")
            lunch_end_raw = raw.get("lunch_end")

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
                if (
                    raw.get("start_time") is not None
                    or raw.get("end_time") is not None
                    or breaks
                    or lunch_start_raw is not None
                    or lunch_end_raw is not None
                ):
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

            if mode == "online":
                if breaks or lunch_start_raw is not None or lunch_end_raw is not None:
                    raise ValidationError({"days": f"Item #{idx}: breaks/lunch are allowed only for office mode."})
            else:
                self._validate_office_breaks_and_lunch(
                    idx=idx,
                    start_time=start_time,
                    end_time=end_time,
                    duration_hours=duration_hours,
                    breaks=breaks,
                    lunch_start_raw=lunch_start_raw,
                    lunch_end_raw=lunch_end_raw,
                )

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
    def _parse_time(value, idx: int, field_name: str, *, minute_step: int = 60):
        if isinstance(value, dt_time):
            parsed = value
        elif isinstance(value, str):
            try:
                parsed = dt_time.fromisoformat(value)
            except ValueError as exc:
                raise ValidationError({"days": f"Item #{idx}: invalid {field_name} format, use HH:MM."}) from exc
        else:
            raise ValidationError({"days": f"Item #{idx}: {field_name} is required."})

        if parsed.second != 0 or parsed.microsecond != 0:
            raise ValidationError({"days": f"Item #{idx}: {field_name} must be in HH:MM format."})
        if minute_step == 60 and parsed.minute != 0:
            raise ValidationError({"days": f"Item #{idx}: {field_name} must be set in full hours (HH:00)."})
        if minute_step != 60 and (parsed.minute % minute_step) != 0:
            raise ValidationError({"days": f"Item #{idx}: {field_name} must use {minute_step}-minute slots."})
        return parsed

    @staticmethod
    def _day_hour_limits(day_date: dt_date):
        if day_date.weekday() < 5:
            return 9, 21
        return 11, 19

    @staticmethod
    def _to_minutes(value: dt_time):
        return value.hour * 60 + value.minute

    def _validate_office_breaks_and_lunch(
        self,
        *,
        idx: int,
        start_time: dt_time,
        end_time: dt_time,
        duration_hours: int,
        breaks,
        lunch_start_raw,
        lunch_end_raw,
    ):
        if duration_hours < 7 and breaks:
            raise ValidationError({"days": f"Item #{idx}: breaks are allowed only when office shift is 7+ hours."})
        if duration_hours < 8 and (lunch_start_raw is not None or lunch_end_raw is not None):
            raise ValidationError({"days": f"Item #{idx}: lunch is allowed only when office shift is 8+ hours."})

        if (lunch_start_raw is None) != (lunch_end_raw is None):
            raise ValidationError({"days": f"Item #{idx}: lunch_start and lunch_end must be set together."})

        shift_start = self._to_minutes(start_time)
        shift_end = self._to_minutes(end_time)
        intervals = []

        if breaks:
            if not isinstance(breaks, list):
                raise ValidationError({"days": f"Item #{idx}: breaks must be an array."})
            if len(breaks) > 4:
                raise ValidationError({"days": f"Item #{idx}: no more than 4 short breaks are allowed."})
            for break_idx, break_item in enumerate(breaks, start=1):
                if not isinstance(break_item, dict):
                    raise ValidationError({"days": f"Item #{idx}: break #{break_idx} must be an object."})
                b_start = self._parse_time(
                    break_item.get("start_time"),
                    idx,
                    f"breaks[{break_idx}].start_time",
                    minute_step=15,
                )
                b_end = self._parse_time(
                    break_item.get("end_time"),
                    idx,
                    f"breaks[{break_idx}].end_time",
                    minute_step=15,
                )
                b_start_m = self._to_minutes(b_start)
                b_end_m = self._to_minutes(b_end)
                if b_end_m <= b_start_m:
                    raise ValidationError({"days": f"Item #{idx}: break #{break_idx} end must be after start."})
                if (b_end_m - b_start_m) != 15:
                    raise ValidationError({"days": f"Item #{idx}: each short break must be exactly 15 minutes."})
                if b_start_m < shift_start or b_end_m > shift_end:
                    raise ValidationError({"days": f"Item #{idx}: break #{break_idx} must be inside shift time."})
                intervals.append((b_start_m, b_end_m, f"break #{break_idx}"))

        if lunch_start_raw is not None and lunch_end_raw is not None:
            lunch_start = self._parse_time(lunch_start_raw, idx, "lunch_start", minute_step=15)
            lunch_end = self._parse_time(lunch_end_raw, idx, "lunch_end", minute_step=15)
            lunch_start_m = self._to_minutes(lunch_start)
            lunch_end_m = self._to_minutes(lunch_end)
            if lunch_end_m <= lunch_start_m:
                raise ValidationError({"days": f"Item #{idx}: lunch end must be after lunch start."})
            if (lunch_end_m - lunch_start_m) != 60:
                raise ValidationError({"days": f"Item #{idx}: lunch must be exactly 60 minutes."})
            if lunch_start_m < shift_start or lunch_end_m > shift_end:
                raise ValidationError({"days": f"Item #{idx}: lunch must be inside shift time."})
            intervals.append((lunch_start_m, lunch_end_m, "lunch"))

        intervals.sort(key=lambda row: row[0])
        prev_end = None
        prev_label = None
        for start_m, end_m, label in intervals:
            if prev_end is not None and start_m < prev_end:
                raise ValidationError({"days": f"Item #{idx}: {label} overlaps with {prev_label}."})
            prev_end = end_m
            prev_label = label

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} - {self.week_start} ({self.status})"


class WeeklyWorkPlanChangeLog(models.Model):
    weekly_plan = models.ForeignKey(
        WeeklyWorkPlan,
        on_delete=models.CASCADE,
        related_name="change_logs",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="weekly_plan_change_logs",
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="changed_weekly_plans_logs",
    )
    week_start = models.DateField()
    changes = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Weekly work plan change log"
        verbose_name_plural = "Weekly work plan change logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["week_start"]),
            models.Index(fields=["user", "week_start"]),
            models.Index(fields=["weekly_plan", "created_at"]),
        ]

    def __str__(self):
        return f"Plan #{self.weekly_plan_id} changes at {self.created_at:%Y-%m-%d %H:%M:%S}"


class WeeklyWorkPlanDeadlineAlert(models.Model):
    week_start = models.DateField(unique=True)
    missing_users = models.JSONField(default=list)
    notified_admins = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Weekly plan deadline alert"
        verbose_name_plural = "Weekly plan deadline alerts"
        ordering = ["-week_start"]
        indexes = [
            models.Index(fields=["week_start"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Deadline alert for week {self.week_start}"
