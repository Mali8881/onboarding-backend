import calendar
from datetime import date

from .models import WorkSchedule, ProductionCalendar, UserWorkSchedule


def get_user_work_schedule(user):
    """
    Возвращает график пользователя или базовый график компании
    """
    try:
        return user.userworkschedule.schedule
    except Exception:
        return WorkSchedule.objects.filter(is_default=True, is_active=True).first()


def get_month_calendar(user, year: int, month: int):
    """
    Возвращает календарь работы пользователя на месяц
    """
    schedule = get_user_work_schedule(user)
    if not schedule:
        raise ValueError("Не задан базовый график работы")

    cal = calendar.Calendar()
    month_days = cal.itermonthdates(year, month)

    result = []

    for day in month_days:
        if day.month != month:
            continue

        # день недели: 0 = Пн, 6 = Вс
        weekday = day.weekday()

        prod_day = ProductionCalendar.objects.filter(date=day).first()

        is_holiday = bool(prod_day and prod_day.is_holiday)
        holiday_name = prod_day.holiday_name if prod_day else ""

        is_working_day = False

        if not is_holiday:
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
