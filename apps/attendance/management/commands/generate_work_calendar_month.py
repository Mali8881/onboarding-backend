from django.core.management.base import BaseCommand

from apps.attendance.services import generate_work_calendar_month


class Command(BaseCommand):
    help = "Generate WorkCalendarDay records for a given month."

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, required=True)
        parser.add_argument("--month", type=int, required=True)
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Update existing records for month if present.",
        )

    def handle(self, *args, **options):
        year = options["year"]
        month = options["month"]
        overwrite = options["overwrite"]
        created, updated = generate_work_calendar_month(year, month, overwrite=overwrite)
        self.stdout.write(
            self.style.SUCCESS(
                f"Work calendar generated for {year:04d}-{month:02d}. created={created}, updated={updated}"
            )
        )

