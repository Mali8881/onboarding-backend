import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser


class Department(models.Model):
    name = models.CharField("Подразделение", max_length=255, unique=True)
    is_active = models.BooleanField("Активен", default=True)  # Добавил verbose_name

    class Meta:
        verbose_name = "Подразделение"
        verbose_name_plural = "Подразделения"

    def __str__(self):
        return self.name


class Position(models.Model):
    name = models.CharField("Должность", max_length=255, unique=True)
    is_active = models.BooleanField("Активна", default=True)  # Добавил verbose_name

    class Meta:
        verbose_name = "Должность"
        verbose_name_plural = "Должности"

    def __str__(self):
        return self.name


class User(AbstractUser):
    avatar = models.ImageField("Аватар", upload_to="avatars/", null=True, blank=True)

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Подразделение"
    )

    position = models.ForeignKey(
        Position,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Должность"
    )

    custom_position = models.CharField(
        "Дополнительная информация о должности",
        max_length=255,
        blank=True,
        null=True  # Добавлено для корректной работы миграций
    )

    # ИЗМЕНЕНО: Вместо default лучше разрешить NULL, чтобы не конфликтовать со старыми записями
    telegram = models.CharField("Telegram", max_length=100, null=True, blank=True)

    phone = models.CharField(
        "Телефон",
        max_length=20,
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
