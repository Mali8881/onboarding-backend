from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.attendance.models import AttendanceMark, WorkCalendarDay

from .models import PayrollEntry, PayrollPeriod, SalaryProfile


User = get_user_model()

WORKED_STATUSES = [
    AttendanceMark.Status.PRESENT,
    AttendanceMark.Status.REMOTE,
]


def month_bounds(year: int, month: int) -> tuple[date, date]:
    first = date(year, month, 1)
    last = date(year, month, monthrange(year, month)[1])
    return first, last


def _planned_days(year: int, month: int) -> int:
    first, last = month_bounds(year, month)
    days = WorkCalendarDay.objects.filter(
        date__range=(first, last),
        is_working_day=True,
    ).count()
    if days > 0:
        return days
    # fallback for months not generated in calendar yet
    return sum(1 for d in range(1, last.day + 1) if date(year, month, d).weekday() < 5)


def _salary_amount(profile: SalaryProfile | None, worked_days: int) -> Decimal:
    if not profile or not profile.is_active:
        return Decimal("0.00")
    if profile.employment_type == SalaryProfile.EmploymentType.FIXED:
        return profile.base_salary
    if profile.employment_type == SalaryProfile.EmploymentType.DAILY:
        return profile.base_salary * Decimal(worked_days)
    # hourly: keep deterministic MVP formula without extra timesheet module
    return profile.base_salary * Decimal(worked_days) * Decimal("8")


@transaction.atomic
def generate_period(year: int, month: int) -> tuple[PayrollPeriod, int, int]:
    period, _ = PayrollPeriod.objects.get_or_create(year=year, month=month)
    if period.status == PayrollPeriod.Status.LOCKED:
        raise ValueError("Period is locked.")

    planned = _planned_days(year, month)
    first, last = month_bounds(year, month)
    users = User.objects.filter(is_active=True).select_related("salary_profile")
    created = 0
    updated = 0

    marks_qs = AttendanceMark.objects.filter(
        user__in=users,
        date__range=(first, last),
        status__in=WORKED_STATUSES,
    )
    worked_map: dict[int, int] = {}
    for row in marks_qs.values("user_id"):
        uid = row["user_id"]
        worked_map[uid] = worked_map.get(uid, 0) + 1

    for user in users:
        worked_days = worked_map.get(user.id, 0)
        profile = getattr(user, "salary_profile", None)
        salary_amount = _salary_amount(profile, worked_days)

        entry, was_created = PayrollEntry.objects.get_or_create(
            user=user,
            period=period,
            defaults={
                "planned_days": planned,
                "worked_days": worked_days,
                "advances": Decimal("0.00"),
                "salary_amount": salary_amount,
                "total_amount": salary_amount,
            },
        )
        if was_created:
            created += 1
            continue

        entry.planned_days = planned
        entry.worked_days = worked_days
        entry.salary_amount = salary_amount
        entry.total_amount = salary_amount - entry.advances
        entry.save(update_fields=["planned_days", "worked_days", "salary_amount", "total_amount", "updated_at"])
        updated += 1

    return period, created, updated

