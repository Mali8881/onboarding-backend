from django.core.management.base import BaseCommand
from django.utils import timezone

from work_schedule.services import notify_admins_about_weekly_plan_deadline_miss


class Command(BaseCommand):
    help = "Checks Monday 12:00 weekly plan deadline and notifies admins about employees who did not submit."

    def handle(self, *args, **options):
        result = notify_admins_about_weekly_plan_deadline_miss(now=timezone.now())
        self.stdout.write(
            self.style.SUCCESS(
                f"weekly_plan_deadline_check: created={result.get('created')} "
                f"reason={result.get('reason')} "
                f"week_start={result.get('week_start')} "
                f"missing_count={result.get('missing_count')} "
                f"notified_admins={result.get('notified_admins', 0)}"
            )
        )
