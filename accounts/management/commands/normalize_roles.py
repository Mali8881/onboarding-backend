from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Role, User


class Command(BaseCommand):
    help = "Оставляет только 4 системные роли и переносит пользователей с лишних ролей на EMPLOYEE."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fallback-role",
            default=Role.Name.EMPLOYEE,
            choices=[Role.Name.EMPLOYEE, Role.Name.INTERN, Role.Name.ADMIN, Role.Name.SUPER_ADMIN],
            help="Роль, в которую будут перенесены пользователи с удаляемых ролей.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Показать, что будет изменено, без записи в БД.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        allowed = {
            Role.Name.SUPER_ADMIN: Role.Level.SUPER_ADMIN,
            Role.Name.ADMIN: Role.Level.ADMIN,
            Role.Name.EMPLOYEE: Role.Level.EMPLOYEE,
            Role.Name.INTERN: Role.Level.INTERN,
        }

        dry_run = options["dry_run"]
        fallback_name = options["fallback_role"]

        fallback_role, _ = Role.objects.get_or_create(
            name=fallback_name,
            defaults={"level": allowed[fallback_name], "description": fallback_name},
        )

        created = 0
        updated = 0
        for name, level in allowed.items():
            role, was_created = Role.objects.get_or_create(
                name=name,
                defaults={"level": level, "description": name},
            )
            if was_created:
                created += 1
            elif role.level != level:
                role.level = level
                role.save(update_fields=["level"])
                updated += 1

        extras = Role.objects.exclude(name__in=allowed.keys())
        extra_count = extras.count()

        moved_users = 0
        if extra_count:
            moved_users = User.objects.filter(role__in=extras).update(role=fallback_role)

        if dry_run:
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING("DRY RUN: изменения не сохранены."))

        self.stdout.write(self.style.SUCCESS(f"Создано системных ролей: {created}"))
        self.stdout.write(self.style.SUCCESS(f"Исправлено уровней ролей: {updated}"))
        self.stdout.write(self.style.SUCCESS(f"Лишних ролей найдено: {extra_count}"))
        self.stdout.write(self.style.SUCCESS(f"Пользователей перенесено в {fallback_name}: {moved_users}"))

        if extra_count and not dry_run:
            deleted, _ = extras.delete()
            self.stdout.write(self.style.SUCCESS(f"Удалено записей (включая m2m-связи): {deleted}"))
