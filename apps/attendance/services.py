from __future__ import annotations

import calendar
import ipaddress
from datetime import date
from datetime import timedelta
from typing import Optional

from django.contrib.auth import get_user_model
from accounts.models import Role
from accounts.access_policy import AccessPolicy

from .models import AttendanceMark, OfficeNetwork, WorkCalendarDay
from work_schedule.models import WeeklyWorkPlan


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
    if include_all_for_admin and AccessPolicy.is_admin_like(actor):
        if not actor.department_id:
            return User.objects.none()
        return User.objects.filter(
            is_active=True,
            department_id=actor.department_id,
            role__name__in=[Role.Name.EMPLOYEE, Role.Name.INTERN],
        ).select_related("position", "department", "role")
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


def office_networks():
    networks = []
    for cidr in OfficeNetwork.objects.filter(is_active=True).values_list("cidr", flat=True):
        try:
            networks.append(ipaddress.ip_network(cidr, strict=False))
        except ValueError:
            continue

    return networks


def is_office_ip(ip_string: str | None) -> bool:
    if not ip_string:
        return False
    try:
        ip = ipaddress.ip_address(ip_string)
        return any(ip in network for network in office_networks())
    except ValueError:
        return False


def get_client_ip(request) -> str | None:
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def planned_work_mode_for_date(*, user, target_date: date) -> str | None:
    week_start = target_date - timedelta(days=target_date.weekday())
    plan = WeeklyWorkPlan.objects.filter(
        user=user,
        status=WeeklyWorkPlan.Status.APPROVED,
        week_start=week_start,
    ).first()
    if not plan:
        return None

    target = target_date.isoformat()
    for item in plan.days or []:
        if not isinstance(item, dict):
            continue
        if item.get("date") != target:
            continue
        mode = item.get("mode")
        if mode in {"office", "online", "day_off"}:
            return mode
    return None
