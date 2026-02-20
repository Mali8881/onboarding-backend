from django.contrib.auth.models import UserManager as DjangoUserManager
from django.apps import apps


class UserManager(DjangoUserManager):

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        Role = apps.get_model("accounts", "Role")
        superadmin_role, _ = Role.objects.get_or_create(
            name=Role.Name.SUPER_ADMIN,
            defaults={
                "level": Role.Level.SUPER_ADMIN,
                "description": "System super administrator",
            },
        )

        extra_fields["role"] = superadmin_role

        return super().create_superuser(username, email, password, **extra_fields)
