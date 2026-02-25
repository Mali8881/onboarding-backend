import calendar
from datetime import date
from datetime import time as dt_time

from .models import WorkSchedule, ProductionCalendar, UserWorkSchedule


def get_user_work_schedule(user):
    """
    Возвращает утверждённый график пользователя
    или базовый график компании
    """
    try:
        uws = user.work_schedule
        if uws.approved:
            return uws.schedule
    except UserWorkSchedule.DoesNotExist:
        pass

    return WorkSchedule.objects.filter(
        is_default=True,
        is_active=True
    ).first()


def get_month_calendar(user, year: int, month: int):
    schedule = get_user_work_schedule(user)
    if not schedule:
        raise ValueError("Не задан базовый график работы")

    cal = calendar.Calendar()
    month_days = cal.itermonthdates(year, month)

    result = []

    for day in month_days:
        if day.month != month:
            continue

        weekday = day.weekday()

        prod_day = ProductionCalendar.objects.filter(date=day).first()

        is_holiday = False
        is_working_day = False
        holiday_name = ""

        if prod_day:
            is_holiday = prod_day.is_holiday
            holiday_name = prod_day.holiday_name or ""

            if prod_day.is_working_day:
                is_working_day = True
            elif not prod_day.is_holiday and weekday in schedule.work_days:
                is_working_day = True
        else:
            if weekday in schedule.work_days:
                is_working_day = True

        day_data = {
            "date": day,
            "weekday": weekday,
            "is_working_day": is_working_day,
            "is_holiday": is_holiday,
            "holiday_name": holiday_name,
            "work_time": None,
            "break_time": None,
        }

        if is_working_day:
            day_data["work_time"] = {
                "start": schedule.start_time,
                "end": schedule.end_time,
            }

            if schedule.break_start and schedule.break_end:
                day_data["break_time"] = {
                    "start": schedule.break_start,
                    "end": schedule.break_end,
                }

        result.append(day_data)

    return result


def generate_production_calendar_month(year: int, month: int, overwrite: bool = False):
    days_in_month = calendar.monthrange(year, month)[1]
    created = 0
    updated = 0

    for day in range(1, days_in_month + 1):
        current_date = date(year, month, day)
        default_is_working = current_date.weekday() < 5
        defaults = {
            "is_working_day": default_is_working,
            "is_holiday": False,
            "holiday_name": "",
        }

        obj, was_created = ProductionCalendar.objects.get_or_create(
            date=current_date,
            defaults=defaults,
        )
        if was_created:
            created += 1
            continue

        if overwrite:
            changed = []
            for field, value in defaults.items():
                if getattr(obj, field) != value:
                    setattr(obj, field, value)
                    changed.append(field)
            if changed:
                obj.save(update_fields=changed)
                updated += 1

    return created, updated


def ensure_user_schedule_for_approved_weekly_plan(plan):
    """
    Ensure approved weekly plan is reflected in UserWorkSchedule list.
    Returns tuple: (assignment, assignment_created, schedule_created)
    """
    assignment = UserWorkSchedule.objects.filter(user=plan.user).select_related("schedule").first()
    if assignment:
        changed_fields = []
        if not assignment.approved:
            assignment.approved = True
            changed_fields.append("approved")
        if changed_fields:
            assignment.save(update_fields=changed_fields)
        return assignment, False, False

    schedule = WorkSchedule.objects.filter(is_active=True, is_default=True).first()
    schedule_created = False

    if not schedule:
        schedule = WorkSchedule.objects.filter(is_active=True).order_by("id").first()

    if not schedule:
        schedule = _build_schedule_from_weekly_plan(plan)
        schedule_created = True

    assignment = UserWorkSchedule.objects.create(
        user=plan.user,
        schedule=schedule,
        approved=True,
    )
    return assignment, True, schedule_created


def _build_schedule_from_weekly_plan(plan):
    work_days = set()
    start_candidates = []
    end_candidates = []

    for item in plan.days or []:
        if not isinstance(item, dict):
            continue
        if item.get("mode") == "day_off":
            continue
        day_raw = item.get("date")
        start_raw = item.get("start_time")
        end_raw = item.get("end_time")
        if not day_raw or not start_raw or not end_raw:
            continue
        try:
            day = day_raw if isinstance(day_raw, date) else date.fromisoformat(str(day_raw))
            start = start_raw if isinstance(start_raw, dt_time) else dt_time.fromisoformat(str(start_raw))
            end = end_raw if isinstance(end_raw, dt_time) else dt_time.fromisoformat(str(end_raw))
        except ValueError:
            continue
        work_days.add(day.weekday())
        start_candidates.append(start)
        end_candidates.append(end)

    if not work_days:
        work_days = {0, 1, 2, 3, 4}
    if not start_candidates:
        start_candidates = [dt_time(hour=9, minute=0)]
    if not end_candidates:
        end_candidates = [dt_time(hour=18, minute=0)]

    return WorkSchedule.objects.create(
        name=f"Auto schedule {plan.user.username} {plan.week_start.isoformat()}",
        work_days=sorted(work_days),
        start_time=min(start_candidates),
        end_time=max(end_candidates),
        break_start=None,
        break_end=None,
        is_default=False,
        is_active=True,
    )
