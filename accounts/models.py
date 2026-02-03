from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        INTERN = "intern", "Стажёр"
        ADMIN = "admin", "Админ"
        SUPERADMIN = "superadmin", "Супер-админ"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.INTERN
    )

    is_blocked = models.BooleanField(default=False)

    # поля профиля (по ТЗ)
    full_name = models.CharField(max_length=255, blank=True)
    telegram = models.CharField(max_length=64, blank=True)
    phone = models.CharField(max_length=32, blank=True)

    def __str__(self):
        return self.username
