import pytest
from datetime import date

from django.contrib.auth import get_user_model

from accounts.models import Role
from work_schedule.models import ProductionCalendar, UserWorkSchedule, WorkSchedule
from work_schedule.services import get_month_calendar


User = get_user_model()


def create_test_user(username="test"):
    role, _ = Role.objects.get_or_create(
        name=Role.Name.EMPLOYEE,
        defaults={"level": Role.Level.EMPLOYEE},
    )
    return User.objects.create_user(username=username, password="StrongPass123!", role=role)


@pytest.mark.django_db
def test_use_default_schedule_if_user_has_none():
    user = create_test_user()

    WorkSchedule.objects.create(
        name="Default",
        work_days=[0, 1, 2, 3, 4],
        start_time="09:00",
        end_time="18:00",
        is_default=True,
        is_active=True,
    )

    calendar = get_month_calendar(user, 2026, 3)

    assert len(calendar) > 0


@pytest.mark.django_db
def test_holiday_overrides_workday():
    user = create_test_user()

    WorkSchedule.objects.create(
        name="Default",
        work_days=[0, 1, 2, 3, 4],
        start_time="09:00",
        end_time="18:00",
        is_default=True,
        is_active=True,
    )

    ProductionCalendar.objects.create(
        date=date(2026, 3, 21),
        is_working_day=False,
        is_holiday=True,
        holiday_name="Nooruz",
    )

    calendar = get_month_calendar(user, 2026, 3)
    day = next(d for d in calendar if d["date"] == date(2026, 3, 21))

    assert day["is_holiday"] is True
    assert day["is_working_day"] is False


@pytest.mark.django_db
def test_weekend_is_not_working_day():
    user = create_test_user()

    WorkSchedule.objects.create(
        name="Default",
        work_days=[0, 1, 2, 3, 4],
        start_time="09:00",
        end_time="18:00",
        is_default=True,
        is_active=True,
    )

    calendar = get_month_calendar(user, 2026, 3)
    sunday = next(d for d in calendar if d["weekday"] == 6)

    assert sunday["is_working_day"] is False


@pytest.mark.django_db
def test_workday_contains_work_time():
    user = create_test_user()

    WorkSchedule.objects.create(
        name="Default",
        work_days=[0, 1, 2, 3, 4],
        start_time="09:00",
        end_time="18:00",
        is_default=True,
        is_active=True,
    )

    calendar = get_month_calendar(user, 2026, 3)
    workday = next(d for d in calendar if d["weekday"] == 0)

    assert workday["work_time"]["start"] is not None
    assert workday["work_time"]["end"] is not None


@pytest.mark.django_db
def test_unapproved_schedule_falls_back_to_default():
    user = create_test_user()

    WorkSchedule.objects.create(
        name="Default",
        work_days=[0, 1, 2, 3, 4],
        start_time="09:00",
        end_time="18:00",
        is_default=True,
        is_active=True,
    )

    custom = WorkSchedule.objects.create(
        name="Custom",
        work_days=[0],
        start_time="10:00",
        end_time="17:00",
        is_active=True,
    )

    UserWorkSchedule.objects.create(
        user=user,
        schedule=custom,
        approved=False,
    )

    calendar = get_month_calendar(user, 2026, 3)
    monday = next(d for d in calendar if d["weekday"] == 0)

    assert monday["work_time"]["start"].strftime("%H:%M") == "09:00"
