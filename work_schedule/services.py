import calendar
from datetime import date

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
