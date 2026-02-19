from django.core.management.base import BaseCommand
from accounts.models import Role, Permission


PERMISSIONS = [
    # Content
    ("content_manage", "Manage content"),
    ("view_content", "View content"),

    # Onboarding / Reports
    ("onboarding_manage", "Manage onboarding"),
    ("reports_review", "Review reports"),
    ("report_submit", "Submit report"),

    # Users
    ("users_manage", "Manage users"),
    ("roles_manage", "Manage roles"),

    # Schedule
    ("schedule_manage", "Manage schedules"),

    # Feedback
    ("feedback_manage", "Manage feedback"),

    # Logs
    ("logs_read", "Read audit logs"),

    # Reference
    ("view_positions", "View positions"),
]


ROLES = {
    "INTERN": [
        "report_submit",
        "view_content",
    ],
    "ADMIN": [
        "content_manage",
        "onboarding_manage",
        "reports_review",
        "users_manage",
        "schedule_manage",
        "feedback_manage",
        "view_content",
    ],
    "SUPER_ADMIN": [
        "content_manage",
        "onboarding_manage",
        "reports_review",
        "users_manage",
        "schedule_manage",
        "feedback_manage",
        "logs_read",
        "roles_manage",
        "view_content",
    ],
}


class Command(BaseCommand):
    help = "Initialize RBAC roles and permissions"

    def handle(self, *args, **options):

        perm_objs = {}

        for code, description in PERMISSIONS:
            p, _ = Permission.objects.get_or_create(
                code=code,
                defaults={"description": description},
            )
            perm_objs[code] = p

        for role_name, perm_codes in ROLES.items():
            role, _ = Role.objects.get_or_create(name=role_name)
            role.permissions.clear()

            for code in perm_codes:
                role.permissions.add(perm_objs[code])

            role.save()

        self.stdout.write(self.style.SUCCESS("RBAC initialized successfully."))
