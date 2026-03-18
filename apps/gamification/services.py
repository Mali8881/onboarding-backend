from datetime import timedelta

from django.utils import timezone

from reports.models import EmployeeDailyReport
from work_schedule.services import resolve_user_shift_for_date

from .models import Badge, UserBadge, UserStreak


DEFAULT_BADGES = [
    {
        "code": "on_time_first",
        "name": "First on-time report",
        "description": "Submitted the first daily report on time.",
    },
    {
        "code": "on_time_streak_7",
        "name": "7-day streak",
        "description": "7 working days in a row with on-time reports.",
    },
    {
        "code": "on_time_streak_30",
        "name": "30-day streak",
        "description": "30 working days in a row with on-time reports.",
    },
]


def _ensure_default_badges():
    for badge in DEFAULT_BADGES:
        Badge.objects.get_or_create(code=badge["code"], defaults=badge)


def _is_workday(user, target_date) -> bool:
    shift = resolve_user_shift_for_date(user, target_date)
    if shift.get("mode") == "day_off":
        return False
    return bool(shift.get("end_time"))


def _has_on_time_report(user, target_date) -> bool:
    return EmployeeDailyReport.objects.filter(
        user=user,
        report_date=target_date,
        is_late=False,
    ).exists()


def compute_current_streak(user, *, reference_date=None, max_days=365) -> int:
    if not user:
        return 0
    date_cursor = reference_date or timezone.localdate()
    streak = 0
    checked = 0
    while checked < max_days:
        if not _is_workday(user, date_cursor):
            date_cursor -= timedelta(days=1)
            checked += 1
            continue
        if _has_on_time_report(user, date_cursor):
            streak += 1
            date_cursor -= timedelta(days=1)
            checked += 1
            continue
        break
    return streak


def update_user_streak(user) -> UserStreak:
    current = compute_current_streak(user)
    last_report = (
        EmployeeDailyReport.objects.filter(user=user, is_late=False)
        .order_by("-report_date")
        .values_list("report_date", flat=True)
        .first()
    )

    streak_obj, _ = UserStreak.objects.get_or_create(user=user)
    streak_obj.current_streak = current
    streak_obj.longest_streak = max(streak_obj.longest_streak, current)
    streak_obj.last_report_date = last_report
    streak_obj.save(update_fields=["current_streak", "longest_streak", "last_report_date", "updated_at"])
    return streak_obj


def _award_badge(user, code: str) -> None:
    badge = Badge.objects.filter(code=code, is_active=True).first()
    if not badge:
        return
    UserBadge.objects.get_or_create(user=user, badge=badge)


def award_on_time_badges(user, *, current_streak=None) -> None:
    if not user:
        return
    _ensure_default_badges()
    if current_streak is None:
        current_streak = compute_current_streak(user)

    on_time_reports_count = EmployeeDailyReport.objects.filter(user=user, is_late=False).count()
    if on_time_reports_count >= 1:
        _award_badge(user, "on_time_first")
    if current_streak >= 7:
        _award_badge(user, "on_time_streak_7")
    if current_streak >= 30:
        _award_badge(user, "on_time_streak_30")
