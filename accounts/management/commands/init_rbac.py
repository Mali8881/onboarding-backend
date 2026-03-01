from django.core.management.base import BaseCommand
from accounts.models import Role, Permission


PERMISSIONS = [
    # Content
    ("content_manage", "content", "Manage content"),
    ("view_content", "content", "View content"),

    # Onboarding / Reports
    ("onboarding_manage", "onboarding", "Manage onboarding"),
    ("reports_review", "reports", "Review reports"),
    ("report_submit", "reports", "Submit report"),

    # Users
    ("users_manage", "accounts", "Manage users"),
    ("roles_manage", "accounts", "Manage roles"),

    # Schedule
    ("schedule_manage", "schedule", "Manage schedules"),

    # Feedback
    ("feedback_manage", "content", "Manage feedback"),

    # Logs
    ("logs_read", "security", "Read audit logs"),

    # Reference
    ("view_positions", "accounts", "View positions"),
]


ROLES = {
    Role.Name.INTERN: [
        "report_submit",
        "view_content",
    ],
    Role.Name.EMPLOYEE: [
        "report_submit",
        "view_content",
        "view_positions",
    ],
    Role.Name.TEAMLEAD: [
        "report_submit",
        "view_content",
        "view_positions",
        "reports_review",
    ],
    Role.Name.DEPARTMENT_HEAD: [
        "content_manage",
        "onboarding_manage",
        "reports_review",
        "users_manage",
        "schedule_manage",
        "feedback_manage",
        "view_content",
        "view_positions",
    ],
    Role.Name.ADMIN: [
        "content_manage",
        "onboarding_manage",
        "reports_review",
        "users_manage",
        "schedule_manage",
        "feedback_manage",
        "logs_read",
        "roles_manage",
        "view_content",
        "view_positions",
    ],
    Role.Name.SUPER_ADMIN: [
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

ROLE_LEVELS = {
    Role.Name.INTERN: Role.Level.INTERN,
    Role.Name.EMPLOYEE: Role.Level.EMPLOYEE,
    Role.Name.TEAMLEAD: Role.Level.TEAMLEAD,
    Role.Name.DEPARTMENT_HEAD: Role.Level.DEPARTMENT_HEAD,
    Role.Name.ADMIN: Role.Level.ADMIN,
    Role.Name.SUPER_ADMIN: Role.Level.SUPER_ADMIN,
}


class Command(BaseCommand):
    help = "Initialize RBAC roles and permissions"

    def handle(self, *args, **options):

        perm_objs = {}

        for codename, module, description in PERMISSIONS:
            p, _ = Permission.objects.get_or_create(
                codename=codename,
                defaults={"module": module, "description": description},
            )
            if p.module != module or p.description != description:
                p.module = module
                p.description = description
                p.save(update_fields=["module", "description"])
            perm_objs[codename] = p

        for role_name, perm_codes in ROLES.items():
            role, _ = Role.objects.get_or_create(
                name=role_name,
                defaults={"level": ROLE_LEVELS[role_name]},
            )
            if role.level != ROLE_LEVELS[role_name]:
                role.level = ROLE_LEVELS[role_name]
                role.save(update_fields=["level"])
            role.permissions.clear()

            for code in perm_codes:
                role.permissions.add(perm_objs[code])

            role.save()

        self.stdout.write(self.style.SUCCESS("RBAC initialized successfully."))
