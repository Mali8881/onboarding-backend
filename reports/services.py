from django.utils import timezone
from .models import Report


ALLOWED_TRANSITIONS = {
    Report.Status.DRAFT: [Report.Status.SENT],
    Report.Status.SENT: [
        Report.Status.ACCEPTED,
        Report.Status.REVISION,
        Report.Status.REJECTED,
    ],
    Report.Status.REVISION: [Report.Status.SENT],
}


def change_report_status(report: Report, new_status: str):
    allowed = ALLOWED_TRANSITIONS.get(report.status, [])

    if new_status not in allowed:
        raise ValueError(
            f"Cannot change status from {report.status} to {new_status}"
        )

    report.status = new_status

    if new_status == Report.Status.SENT:
        report.submitted_at = timezone.now()

    report.save(update_fields=["status", "submitted_at"])
