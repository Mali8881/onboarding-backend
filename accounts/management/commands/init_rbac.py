from django.core.management.base import BaseCommand
from accounts.models import Role, Permission


PERMISSIONS = [
    # Users Management
    ("users.view", "users", "View users list/profile"),
    ("users.create", "users", "Create users"),
    ("users.edit", "users", "Edit users"),
    ("users.activate", "users", "Activate users"),
    ("users.deactivate", "users", "Deactivate users"),
    ("users.assign_role", "users", "Assign role except super admin"),

    # Onboarding Management
    ("onboarding.view", "onboarding", "View onboarding"),
    ("onboarding.create", "onboarding", "Create onboarding programs"),
    ("onboarding.edit", "onboarding", "Edit onboarding programs"),
    ("onboarding.delete", "onboarding", "Delete onboarding programs"),
    ("onboarding_day.create", "onboarding", "Create onboarding day"),
    ("onboarding_day.edit", "onboarding", "Edit onboarding day"),
    ("onboarding_day.delete", "onboarding", "Delete onboarding day"),
    ("onboarding_report.view", "onboarding", "View onboarding reports"),
    ("onboarding_report.review", "onboarding", "Review onboarding reports"),

    # Content Management
    ("content.view", "content", "View corporate content"),
    ("content.create", "content", "Create corporate content"),
    ("content.edit", "content", "Edit corporate content"),
    ("content.delete", "content", "Delete corporate content"),
    ("news.create", "content", "Create news"),
    ("news.edit", "content", "Edit news"),
    ("news.delete", "content", "Delete news"),
    ("team.edit", "content", "Manage team block"),
    ("welcome_block.edit", "content", "Manage welcome block"),

    # Schedule Management
    ("schedule.view", "schedule", "View schedules"),
    ("schedule.create", "schedule", "Create schedules"),
    ("schedule.edit", "schedule", "Edit schedules"),
    ("schedule.delete", "schedule", "Delete schedules"),
    ("schedule.assign", "schedule", "Assign schedules to users"),

    # Feedback Management
    ("feedback.view", "feedback", "View feedback"),
    ("feedback.update_status", "feedback", "Update feedback status"),
    ("feedback.resolve", "feedback", "Resolve feedback"),

    # Super administrator domain
    ("logs_read", "security", "Read audit logs"),
    ("roles_manage", "accounts", "Manage roles and role permissions"),
    ("security.settings", "security", "Manage security settings"),
    ("security.password_policy", "security", "Manage password policy"),
    ("security.session_settings", "security", "Manage session settings"),
    ("security.2fa_settings", "security", "Manage 2FA settings"),
    ("security.audit_logs", "security", "Access audit logs"),
    ("role.create", "roles", "Create roles"),
    ("role.edit", "roles", "Edit roles"),
    ("role.delete", "roles", "Delete roles"),
    ("role.assign_super_admin", "roles", "Assign super admin role"),
    ("system.settings", "system", "Manage system settings"),
    ("system.interface_settings", "system", "Manage interface settings"),
    ("system.branding_settings", "system", "Manage branding settings"),
    ("system.global_config", "system", "Manage global config"),

    # Legacy permissions used by existing views
    ("content_manage", "content", "Manage content (legacy)"),
    ("view_content", "content", "View content (legacy)"),
    ("onboarding_manage", "onboarding", "Manage onboarding (legacy)"),
    ("reports_review", "reports", "Review reports (legacy)"),
    ("report_submit", "reports", "Submit report"),
    ("users_manage", "accounts", "Manage users (legacy)"),
    ("schedule_manage", "schedule", "Manage schedules (legacy)"),
    ("feedback_manage", "content", "Manage feedback (legacy)"),
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
    Role.Name.ADMINISTRATOR: [
        "users.view",
        "users.create",
        "users.edit",
        "users.activate",
        "users.deactivate",
        "users.assign_role",
        "onboarding.view",
        "onboarding.create",
        "onboarding.edit",
        "onboarding.delete",
        "onboarding_day.create",
        "onboarding_day.edit",
        "onboarding_day.delete",
        "onboarding_report.view",
        "onboarding_report.review",
        "content.view",
        "content.create",
        "content.edit",
        "content.delete",
        "news.create",
        "news.edit",
        "news.delete",
        "team.edit",
        "welcome_block.edit",
        "schedule.view",
        "schedule.create",
        "schedule.edit",
        "schedule.delete",
        "schedule.assign",
        "feedback.view",
        "feedback.update_status",
        "feedback.resolve",
        "content_manage",
        "onboarding_manage",
        "reports_review",
        "users_manage",
        "schedule_manage",
        "feedback_manage",
        "view_content",
        "view_positions",
    ],
    # Legacy operational role kept for backward compatibility.
    Role.Name.ADMIN: [
        "users.view",
        "users.create",
        "users.edit",
        "users.activate",
        "users.deactivate",
        "users.assign_role",
        "onboarding.view",
        "onboarding.create",
        "onboarding.edit",
        "onboarding.delete",
        "onboarding_day.create",
        "onboarding_day.edit",
        "onboarding_day.delete",
        "onboarding_report.view",
        "onboarding_report.review",
        "content.view",
        "content.create",
        "content.edit",
        "content.delete",
        "news.create",
        "news.edit",
        "news.delete",
        "team.edit",
        "welcome_block.edit",
        "schedule.view",
        "schedule.create",
        "schedule.edit",
        "schedule.delete",
        "schedule.assign",
        "feedback.view",
        "feedback.update_status",
        "feedback.resolve",
        "content_manage",
        "onboarding_manage",
        "reports_review",
        "users_manage",
        "schedule_manage",
        "feedback_manage",
        "view_content",
        "view_positions",
    ],
    Role.Name.SUPER_ADMIN: [
        "logs_read",
        "roles_manage",
        "security.settings",
        "security.password_policy",
        "security.session_settings",
        "security.2fa_settings",
        "security.audit_logs",
        "role.create",
        "role.edit",
        "role.delete",
        "role.assign_super_admin",
        "system.settings",
        "system.interface_settings",
        "system.branding_settings",
        "system.global_config",
    ],
}

ROLE_LEVELS = {
    Role.Name.INTERN: Role.Level.INTERN,
    Role.Name.EMPLOYEE: Role.Level.EMPLOYEE,
    Role.Name.ADMINISTRATOR: Role.Level.ADMINISTRATOR,
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
