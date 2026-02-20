from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import PasswordResetToken
from common.models import Notification
from onboarding_core.models import OnboardingDay, OnboardingProgress
from reports.models import OnboardingReport, OnboardingReportLog, ReportNotification


class Command(BaseCommand):
    help = "Prepare a clean, predictable DB state for E2E API checks."

    def add_arguments(self, parser):
        parser.add_argument(
            "--keep-progress",
            action="store_true",
            help="Do not clear onboarding progress.",
        )
        parser.add_argument(
            "--keep-notifications",
            action="store_true",
            help="Do not clear common notifications.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        keep_progress = options["keep_progress"]
        keep_notifications = options["keep_notifications"]

        reports_deleted = OnboardingReport.objects.count()
        report_logs_deleted = OnboardingReportLog.objects.count()
        report_notifications_deleted = ReportNotification.objects.count()
        reset_tokens_deleted = PasswordResetToken.objects.count()
        common_notifications_deleted = Notification.objects.count()
        progress_deleted = OnboardingProgress.objects.count()

        # Keep dependent rows consistent: delete reports first, then logs/notifications.
        OnboardingReport.objects.all().delete()
        OnboardingReportLog.objects.all().delete()
        ReportNotification.objects.all().delete()
        PasswordResetToken.objects.all().delete()

        if not keep_notifications:
            Notification.objects.all().delete()

        if not keep_progress:
            OnboardingProgress.objects.all().delete()

        normalized_days = self._normalize_day_numbers()

        self.stdout.write(self.style.SUCCESS("E2E preparation complete."))
        self.stdout.write(
            f"Normalized onboarding days: {normalized_days}; "
            f"reports deleted: {reports_deleted}; "
            f"report logs deleted: {report_logs_deleted}; "
            f"report notifications deleted: {report_notifications_deleted}; "
            f"password reset tokens deleted: {reset_tokens_deleted}; "
            f"progress deleted: {0 if keep_progress else progress_deleted}; "
            f"common notifications deleted: {0 if keep_notifications else common_notifications_deleted}"
        )

    def _normalize_day_numbers(self):
        days = list(OnboardingDay.objects.order_by("position", "day_number", "id"))
        if not days:
            return 0

        # First pass: move to temp values to avoid unique collisions.
        temp_base = 10000
        for idx, day in enumerate(days, start=1):
            OnboardingDay.objects.filter(pk=day.pk).update(day_number=temp_base + idx)

        # Second pass: write final sequential day numbers.
        for idx, day in enumerate(days, start=1):
            OnboardingDay.objects.filter(pk=day.pk).update(day_number=idx)

        return len(days)
