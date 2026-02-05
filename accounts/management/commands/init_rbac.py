from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from accounts.models import User

# Минимальный набор прав под MVP по ТЗ
PERMISSIONS = [
    ("content_manage", "Can manage content"),
    ("onboarding_manage", "Can manage onboarding"),
    ("reports_review", "Can review reports"),
    ("users_manage", "Can manage users"),
    ("schedule_manage", "Can manage schedules"),
    ("feedback_manage", "Can manage feedback"),
    ("logs_read", "Can read audit logs"),
    ("roles_manage", "Can manage roles and permissions"),
]

GROUPS = {
    "INTERN": [],
    "ADMIN_CONTENT": ["content_manage"],
    "ADMIN_REPORTS": ["onboarding_manage", "reports_review"],
    "ADMIN_USERS": ["users_manage"],
    "ADMIN_SUPPORT": ["feedback_manage", "schedule_manage"],
    "SUPER_ADMIN": ["content_manage", "onboarding_manage", "reports_review", "users_manage",
                    "schedule_manage", "feedback_manage", "logs_read", "roles_manage"],
}


class Command(BaseCommand):
    help = "Initialize RBAC groups and permissions"

    def handle(self, *args, **options):
        ct = ContentType.objects.get_for_model(User)

        perm_objs = {}
        for codename, name in PERMISSIONS:
            p, _ = Permission.objects.get_or_create(
                codename=codename,
                content_type=ct,
                defaults={"name": name},
            )
            perm_objs[codename] = p

        for group_name, perm_codes in GROUPS.items():
            g, _ = Group.objects.get_or_create(name=group_name)
            g.permissions.clear()
            for code in perm_codes:
                g.permissions.add(perm_objs[code])
            g.save()

        self.stdout.write(self.style.SUCCESS("RBAC initialized: groups + permissions created."))
