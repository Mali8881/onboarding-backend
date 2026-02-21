from __future__ import annotations

import calendar
from datetime import date
from typing import Optional

from django.contrib.auth import get_user_model

from .models import AttendanceMark, WorkCalendarDay


User = get_user_model()


def month_bounds(year: int, month: int) -> tuple[date, date]:
    first = date(year, month, 1)
    last = date(year, month, calendar.monthrange(year, month)[1])
    return first, last


def generate_work_calendar_month(year: int, month: int, *, overwrite: bool = False) -> tuple[int, int]:
    """
    Create/update WorkCalendarDay records for a month.

    Default rule:
    - Mon-Fri working days
    - Sat/Sun non-working days
    """
    _, last = month_bounds(year, month)
    created = 0
    updated = 0

    for day in range(1, last.day + 1):
        current = date(year, month, day)
        defaults = {
            "is_working_day": current.weekday() < 5,
            "is_holiday": False,
            "note": "",
        }

        if overwrite:
            obj, _ = WorkCalendarDay.objects.update_or_create(
                date=current,
                defaults=defaults,
            )
            if _:
                created += 1
            else:
                updated += 1
            continue

        _, was_created = WorkCalendarDay.objects.get_or_create(
            date=current,
            defaults=defaults,
        )
        if was_created:
            created += 1

    return created, updated


def attendance_table_queryset(actor, *, include_all_for_admin: bool = True):
    if actor.is_anonymous:
        return User.objects.none()
    if hasattr(actor, "is_admin_like") and actor.is_admin_like and include_all_for_admin:
        return User.objects.filter(is_active=True).select_related("position", "department", "role")
    if actor.team_members.exists():
        return actor.team_members.filter(is_active=True).select_related("position", "department", "role")
    return User.objects.filter(id=actor.id).select_related("position", "department", "role")


def build_attendance_table(*, users, year: int, month: int, status_filter: Optional[str] = None):
    first, last = month_bounds(year, month)
    marks_qs = AttendanceMark.objects.filter(
        user__in=users,
        date__range=(first, last),
    ).select_related("user")
    if status_filter:
        marks_qs = marks_qs.filter(status=status_filter)

    marks_map = {}
    for mark in marks_qs:
        marks_map.setdefault(mark.user_id, {})[mark.date.isoformat()] = {
            "status": mark.status,
            "comment": mark.comment,
        }

    days = [date(year, month, d).isoformat() for d in range(1, last.day + 1)]
    rows = []
    for user in users:
        rows.append(
            {
                "user_id": user.id,
                "username": user.username,
                "full_name": f"{user.first_name} {user.last_name}".strip() or user.username,
                "position": user.position.name if user.position_id else user.custom_position,
                "department_id": user.department_id,
                "marks": marks_map.get(user.id, {}),
            }
        )

    return {"days": days, "rows": rows}
