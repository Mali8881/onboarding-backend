from django.db import migrations


def forwards(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Permission = apps.get_model("accounts", "Permission")

    # Role levels aligned with accounts.models.Role.Level
    LEVEL_DEPARTMENT_HEAD = 40
    LEVEL_ADMIN = 45
    LEVEL_SUPER_ADMIN = 50

    def get_or_none(name):
        return Role.objects.filter(name=name).first()

    old_admin = get_or_none("ADMIN")
    department_head = get_or_none("DEPARTMENT_HEAD")

    # Migrate legacy ADMIN (department admin) -> DEPARTMENT_HEAD.
    if old_admin and not department_head:
        old_admin.name = "DEPARTMENT_HEAD"
        old_admin.level = LEVEL_DEPARTMENT_HEAD
        old_admin.save(update_fields=["name", "level"])
        department_head = old_admin
        old_admin = None

    if not department_head:
        department_head = Role.objects.create(name="DEPARTMENT_HEAD", level=LEVEL_DEPARTMENT_HEAD)
    elif department_head.level != LEVEL_DEPARTMENT_HEAD:
        department_head.level = LEVEL_DEPARTMENT_HEAD
        department_head.save(update_fields=["level"])

    # Create new high ADMIN role if missing.
    admin = get_or_none("ADMIN")
    if not admin:
        admin = Role.objects.create(name="ADMIN", level=LEVEL_ADMIN)
    elif admin.level != LEVEL_ADMIN:
        admin.level = LEVEL_ADMIN
        admin.save(update_fields=["level"])

    super_admin = get_or_none("SUPER_ADMIN")
    if super_admin and super_admin.level != LEVEL_SUPER_ADMIN:
        super_admin.level = LEVEL_SUPER_ADMIN
        super_admin.save(update_fields=["level"])

    permission_map = {
        item.codename: item.id
        for item in Permission.objects.filter(
            codename__in=[
                "content_manage",
                "onboarding_manage",
                "reports_review",
                "users_manage",
                "schedule_manage",
                "feedback_manage",
                "view_content",
                "view_positions",
                "logs_read",
                "roles_manage",
            ]
        )
    }

    department_head_permissions = [
        "content_manage",
        "onboarding_manage",
        "reports_review",
        "users_manage",
        "schedule_manage",
        "feedback_manage",
        "view_content",
        "view_positions",
    ]
    admin_permissions = department_head_permissions + ["logs_read", "roles_manage"]

    department_head.permissions.set(
        [permission_map[code] for code in department_head_permissions if code in permission_map]
    )
    admin.permissions.set([permission_map[code] for code in admin_permissions if code in permission_map])


def backwards(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")

    department_head = Role.objects.filter(name="DEPARTMENT_HEAD").first()
    admin = Role.objects.filter(name="ADMIN").first()

    # Revert to legacy shape: keep ADMIN as old role.
    if department_head and not admin:
        department_head.name = "ADMIN"
        department_head.level = 40
        department_head.save(update_fields=["name", "level"])
        return

    if department_head and admin:
        # Keep existing ADMIN and drop DEPARTMENT_HEAD on rollback.
        department_head.delete()
        if admin.level != 40:
            admin.level = 40
            admin.save(update_fields=["level"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_promotion_request"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]

