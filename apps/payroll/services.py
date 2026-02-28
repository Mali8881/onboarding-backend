from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import DecimalField, ExpressionWrapper, F, Sum, Value
from django.db.models.functions import Coalesce

from accounts.models import Role
from apps.attendance.models import AttendanceMark

from .models import HourlyRateHistory, PayrollCompensation, PayrollRecord


User = get_user_model()
ZERO = Decimal("0.00")


def month_start(year: int, month: int) -> date:
    return date(year, month, 1)


def month_bounds(year: int, month: int) -> tuple[date, date]:
    first = month_start(year, month)
    last = date(year, month, monthrange(year, month)[1])
    return first, last


@dataclass(frozen=True)
class RecalculateResult:
    created: int
    updated: int


class PayrollService:
    @staticmethod
    def get_or_create_compensation(*, user) -> PayrollCompensation:
        compensation, _ = PayrollCompensation.objects.get_or_create(
            user=user,
            defaults={
                "pay_type": PayrollCompensation.PayType.HOURLY,
                "hourly_rate": user.current_hourly_rate,
                "minute_rate": ZERO,
                "fixed_salary": ZERO,
            },
        )
        return compensation

    @staticmethod
    def set_hourly_rate(*, user, rate: Decimal, start_date: date) -> HourlyRateHistory:
        compensation = PayrollService.get_or_create_compensation(user=user)
        compensation.pay_type = PayrollCompensation.PayType.HOURLY
        compensation.hourly_rate = rate
        compensation.save(update_fields=["pay_type", "hourly_rate", "updated_at"])

        if not HourlyRateHistory.objects.filter(user=user, start_date__lt=start_date).exists():
            HourlyRateHistory.objects.get_or_create(
                user=user,
                start_date=date(2000, 1, 1),
                defaults={"rate": user.current_hourly_rate},
            )

        user.current_hourly_rate = rate
        user.save(update_fields=["current_hourly_rate"])

        history, _ = HourlyRateHistory.objects.update_or_create(
            user=user,
            start_date=start_date,
            defaults={"rate": rate},
        )
        return history

    @classmethod
    def _rate_segments(
        cls,
        *,
        user,
        period_start: date,
        period_end: date,
        base_hourly_rate: Decimal,
    ) -> list[tuple[date, date, Decimal]]:
        points = list(
            HourlyRateHistory.objects.filter(user=user, start_date__lte=period_end)
            .order_by("start_date")
            .values("start_date", "rate")
        )

        if not points:
            return [(period_start, period_end, base_hourly_rate)]

        base_rate = base_hourly_rate
        for point in points:
            if point["start_date"] <= period_start:
                base_rate = point["rate"]
            else:
                break

        segments: list[tuple[date, date, Decimal]] = []
        cursor = period_start
        current_rate = base_rate

        for point in points:
            change_start = point["start_date"]
            if change_start <= period_start:
                continue
            if change_start > period_end:
                break

            segment_end = change_start - timedelta(days=1)
            if cursor <= segment_end:
                segments.append((cursor, segment_end, current_rate))
            cursor = change_start
            current_rate = point["rate"]

        if cursor <= period_end:
            segments.append((cursor, period_end, current_rate))

        return segments

    @classmethod
    def _salary_for_month(cls, *, user, period_start: date, period_end: date) -> tuple[Decimal, Decimal]:
        compensation = cls.get_or_create_compensation(user=user)
        if compensation.pay_type == PayrollCompensation.PayType.FIXED_SALARY:
            total_hours = AttendanceMark.objects.filter(user=user, date__range=(period_start, period_end)).aggregate(
                hours=Coalesce(Sum("actual_hours"), ZERO)
            )["hours"]
            return total_hours, compensation.fixed_salary

        if compensation.pay_type == PayrollCompensation.PayType.MINUTE:
            values = AttendanceMark.objects.filter(user=user, date__range=(period_start, period_end)).annotate(
                row_salary=ExpressionWrapper(
                    F("actual_hours") * Value(Decimal("60.00")) * Value(compensation.minute_rate),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            ).aggregate(
                hours=Coalesce(Sum("actual_hours"), ZERO),
                salary=Coalesce(Sum("row_salary"), ZERO),
            )
            return values["hours"], values["salary"]

        segments = cls._rate_segments(
            user=user,
            period_start=period_start,
            period_end=period_end,
            base_hourly_rate=compensation.hourly_rate,
        )
        total_hours = ZERO
        total_salary = ZERO

        for seg_start, seg_end, rate in segments:
            qs = AttendanceMark.objects.filter(user=user, date__range=(seg_start, seg_end))
            values = qs.annotate(
                row_salary=ExpressionWrapper(
                    F("actual_hours") * Value(rate),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            ).aggregate(
                hours=Coalesce(Sum("actual_hours"), ZERO),
                salary=Coalesce(Sum("row_salary"), ZERO),
            )
            total_hours += values["hours"]
            total_salary += values["salary"]

        return total_hours, total_salary

    @classmethod
    @transaction.atomic
    def recalculate_month(cls, *, year: int, month: int) -> RecalculateResult:
        period_start, period_end = month_bounds(year, month)
        users = User.objects.filter(is_active=True).exclude(role__name=Role.Name.INTERN).select_related("role")

        totals_by_user = {
            row["user_id"]: row["total_hours"]
            for row in AttendanceMark.objects.filter(date__range=(period_start, period_end))
            .values("user_id")
            .annotate(total_hours=Coalesce(Sum(F("actual_hours")), ZERO))
        }

        created = 0
        updated = 0

        for user in users:
            total_hours, rate_salary = cls._salary_for_month(user=user, period_start=period_start, period_end=period_end)
            if user.id not in totals_by_user:
                total_hours = ZERO
                rate_salary = ZERO

            record, was_created = PayrollRecord.objects.get_or_create(
                user=user,
                month=period_start,
                defaults={
                    "total_hours": total_hours,
                    "total_salary": rate_salary,
                    "bonus": ZERO,
                    "status": PayrollRecord.Status.CALCULATED,
                },
            )

            if was_created:
                created += 1
                continue

            record.total_hours = total_hours
            record.total_salary = rate_salary + record.bonus
            record.status = PayrollRecord.Status.CALCULATED
            record.save(update_fields=["total_hours", "total_salary", "status", "calculated_at", "updated_at"])
            updated += 1

        return RecalculateResult(created=created, updated=updated)
