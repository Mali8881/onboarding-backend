from django.utils import timezone


def is_deadline_passed(day):
    if not day.deadline_time:
        return False

    now = timezone.localtime()

    deadline_dt = timezone.make_aware(
        timezone.datetime(
            year=now.year,
            month=now.month,
            day=now.day,
            hour=day.deadline_time.hour,
            minute=day.deadline_time.minute,
        )
    )

    return now > deadline_dt

