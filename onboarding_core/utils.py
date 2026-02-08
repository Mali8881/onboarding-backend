from django.utils import timezone


def is_deadline_passed(day):
    if not day.deadline_time:
        return False

    now = timezone.localtime()
    deadline_dt = now.replace(
        hour=day.deadline_time.hour,
        minute=day.deadline_time.minute,
        second=0,
        microsecond=0,
    )

    return now > deadline_dt
