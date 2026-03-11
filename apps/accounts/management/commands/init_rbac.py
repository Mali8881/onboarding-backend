from django.core.management.base import BaseCommand
from apps.accounts.models import Role, Permission


PERMISSIONS = [
    # Users Management
    ("users.view", "users", "View users list/profile"),
    ("users.create", "users", "Create users"),
    ("users.edit", "users", "Edit users"),
    ("users.activate", "users", "Activate users"),
    ("users.deactivate", "users", "Deactivate users"),
    ("users.delete", "users", "Delete users (soft-delete)"),
    ("users.assign_role", "users", "Assign role except super admin"),

    # Onboarding Management
    ("onboarding.view", "onboarding", "View onboarding programs"),
    ("onboarding.create", "onboarding", "Create onboarding programs"),
    ("onboarding.edit", "onboarding", "Edit onboarding programs"),
    ("onboarding.delete", "onboarding", "Delete onboarding programs"),
    ("onboarding_day.create", "onboarding", "Create onboarding day"),
    ("onboarding_day.edit", "onboarding", "Edit onboarding day"),
    ("onboarding_day.delete", "onboarding", "Delete onboarding day"),
    ("onboarding_report.view", "onboarding", "View onboarding reports"),
    ("onboarding_report.review", "onboarding", "Review/approve onboarding reports"),
    ("onboarding_report.submit", "onboarding", "Submit own daily onboarding report"),
    ("onboarding.assign_program", "onboarding", "Assign onboarding program to intern"),

    # Org Structure
    ("org.view", "org", "View org structure (departments, positions)"),
    ("org.manage", "org", "Create/edit/delete departments and positions"),

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

    # Tasks (Kanban)
    ("tasks.view", "tasks", "View tasks (scoped by role)"),
    ("tasks.create", "tasks", "Create tasks (scoped by role)"),
    ("tasks.edit", "tasks", "Edit tasks (scoped by role)"),
    ("tasks.delete", "tasks", "Delete tasks (scoped by role)"),
    ("tasks.manage_team", "tasks", "Manage tasks of entire team/all users"),

    # BPM (Business Processes)
    ("bpm.view", "bpm", "View process instances (scoped by role)"),
    ("bpm.create", "bpm", "Create process instances"),
    ("bpm.edit", "bpm", "Edit process instances (scoped by role)"),
    ("bpm.delete", "bpm", "Delete process instances (scoped by role)"),
    ("bpm.approve_step", "bpm", "Approve/close BPM steps"),
    ("bpm.manage_templates", "bpm", "Create/edit/delete process templates"),

    # Attendance
    ("attendance.view_own", "attendance", "View own attendance marks"),
    ("attendance.view_team", "attendance", "View team attendance marks"),
    ("attendance.mark_own", "attendance", "Create/edit own attendance mark"),
    ("attendance.manage", "attendance", "Full attendance management for all users"),
    ("attendance.approve", "attendance", "Approve attendance marks for team"),
    ("attendance.calendar", "attendance", "Manage work calendar"),

    # Payroll
    ("payroll.view_own", "payroll", "View own payroll/salary"),
    ("payroll.manage", "payroll", "Full payroll management (periods, entries, salary profiles)"),

    # Knowledge Base
    ("kb.view", "kb", "View KB articles (scoped by visibility)"),
    ("kb.create", "kb", "Create KB articles"),
    ("kb.edit", "kb", "Edit KB articles"),
    ("kb.delete", "kb", "Delete KB articles"),
    ("kb.publish", "kb", "Publish/unpublish KB articles"),
    ("kb.manage_categories", "kb", "Manage KB categories"),
    ("kb.view_analytics", "kb", "View KB read analytics"),

    # Metrics & Dashboards
    ("metrics.view_own", "metrics", "View own performance metrics"),
    ("metrics.view_team", "metrics", "View team performance metrics"),
    ("metrics.manage", "metrics", "Create/edit/delete metric definitions"),

    # Calendar
    ("calendar.view", "calendar", "View calendar events"),
    ("calendar.create", "calendar", "Create calendar events (scoped by role)"),
    ("calendar.edit", "calendar", "Edit calendar events (scoped by role)"),
    ("calendar.delete", "calendar", "Delete calendar events"),

    # Audit Log
    ("audit.view", "security", "View audit log"),
    ("audit.delete", "security", "Delete audit records"),

    # Super Administrator domain
    ("logs_read", "security", "Read audit logs (legacy)"),
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

    # Legacy permissions kept for backward compatibility with existing views
    ("content_manage", "content", "Manage content (legacy)"),
    ("view_content", "content", "View content (legacy)"),
    ("onboarding_manage", "onboarding", "Manage onboarding (legacy)"),
    ("reports_review", "reports", "Review reports (legacy)"),
    ("report_submit", "reports", "Submit report (legacy)"),
    ("users_manage", "accounts", "Manage users (legacy)"),
    ("schedule_manage", "schedule", "Manage schedules (legacy)"),
    ("feedback_manage", "content", "Manage feedback (legacy)"),
    ("view_positions", "accounts", "View positions (legacy)"),
]


# Permissions shared by Intern and Employee (basic authenticated user access)
_BASE_USER_PERMS = [
    "view_content",
    "view_positions",
    "org.view",
    # Tasks: own only (scoped in TaskPolicy)
    "tasks.view",
    "tasks.create",
    "tasks.edit",
    # BPM: own processes (scoped in BPM views)
    "bpm.view",
    "bpm.create",
    "bpm.approve_step",
    # Attendance: own marks (scoped in AttendancePolicy)
    "attendance.view_own",
    "attendance.mark_own",
    # KB: filtered by visibility
    "kb.view",
    # Metrics: own only
    "metrics.view_own",
    # Calendar: view events
    "calendar.view",
    # Payroll: own salary
    "payroll.view_own",
]

# Operational admin permissions shared by Admin and Administrator
_OPERATIONAL_ADMIN_PERMS = [
    # Users
    "users.view",
    "users.create",
    "users.edit",
    "users.activate",
    "users.deactivate",
    "users.assign_role",
    # Org
    "org.view",
    "org.manage",
    # Onboarding
    "onboarding.view",
    "onboarding.create",
    "onboarding.edit",
    "onboarding.delete",
    "onboarding_day.create",
    "onboarding_day.edit",
    "onboarding_day.delete",
    "onboarding_report.view",
    "onboarding_report.review",
    "onboarding.assign_program",
    # Content
    "content.view",
    "content.create",
    "content.edit",
    "content.delete",
    "news.create",
    "news.edit",
    "news.delete",
    "team.edit",
    "welcome_block.edit",
    # Schedule
    "schedule.view",
    "schedule.create",
    "schedule.edit",
    "schedule.delete",
    "schedule.assign",
    # Feedback
    "feedback.view",
    "feedback.update_status",
    "feedback.resolve",
    # Tasks: full management
    "tasks.view",
    "tasks.create",
    "tasks.edit",
    "tasks.delete",
    "tasks.manage_team",
    # BPM: full management
    "bpm.view",
    "bpm.create",
    "bpm.edit",
    "bpm.delete",
    "bpm.approve_step",
    "bpm.manage_templates",
    # Attendance: full management
    "attendance.view_own",
    "attendance.view_team",
    "attendance.mark_own",
    "attendance.manage",
    "attendance.approve",
    "attendance.calendar",
    # Payroll: full management
    "payroll.view_own",
    "payroll.manage",
    # KB: full management
    "kb.view",
    "kb.create",
    "kb.edit",
    "kb.delete",
    "kb.publish",
    "kb.manage_categories",
    "kb.view_analytics",
    # Metrics: full access
    "metrics.view_own",
    "metrics.view_team",
    "metrics.manage",
    # Calendar: full management
    "calendar.view",
    "calendar.create",
    "calendar.edit",
    "calendar.delete",
    # Audit: view (not delete)
    "audit.view",
    # Legacy
    "content_manage",
    "view_content",
    "view_positions",
    "onboarding_manage",
    "reports_review",
    "users_manage",
    "schedule_manage",
    "feedback_manage",
]

ROLES = {
    Role.Name.INTERN: [
        *_BASE_USER_PERMS,
        # Onboarding: only own program and daily reports
        "onboarding.view",
        "onboarding_report.submit",
        # Legacy
        "report_submit",
    ],
    Role.Name.EMPLOYEE: [
        *_BASE_USER_PERMS,
        # Onboarding: only if assigned as mentor/participant
        "onboarding.view",
        # Legacy
        "report_submit",
    ],
    Role.Name.TEAMLEAD: [
        *_BASE_USER_PERMS,
        # Users: view/edit own team (scoped in AccessPolicy.can_view_user / can_manage_user)
        "users.view",
        "users.edit",
        # Onboarding: view programs + review team reports + assign to own interns
        "onboarding.view",
        "onboarding_report.view",
        "onboarding_report.review",
        "onboarding.assign_program",
        # Tasks: team management
        "tasks.delete",
        "tasks.manage_team",
        # BPM: edit team processes
        "bpm.edit",
        # Attendance: view + manage own team
        "attendance.view_team",
        "attendance.approve",
        # KB: create/edit/publish as department content editor
        "kb.create",
        "kb.edit",
        "kb.publish",
        "kb.view_analytics",
        # Metrics: team view
        "metrics.view_team",
        # Calendar: create/edit events for own team
        "calendar.create",
        "calendar.edit",
        # Legacy
        "report_submit",
        "reports_review",
    ],
    # Administrator: operational admin role (users, onboarding, content, schedule, feedback)
    # Does NOT manage system security or role definitions — that is SuperAdmin's domain.
    Role.Name.ADMINISTRATOR: _OPERATIONAL_ADMIN_PERMS,
    # Admin: legacy alias for Administrator, kept for backward compatibility.
    # Has identical permissions to ADMINISTRATOR.
    Role.Name.ADMIN: _OPERATIONAL_ADMIN_PERMS,
    Role.Name.SUPER_ADMIN: [
        # SuperAdmin inherits all operational permissions as safety fallback
        *_OPERATIONAL_ADMIN_PERMS,
        # Plus: delete users
        "users.delete",
        # Plus: audit log full access
        "audit.delete",
        # Plus: security, roles, system configuration
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
    Role.Name.TEAMLEAD: Role.Level.TEAMLEAD,
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
