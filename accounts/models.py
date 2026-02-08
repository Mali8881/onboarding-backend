from django.db import models
from django.contrib.auth.models import AbstractUser


class Department(models.Model):
    name = models.CharField("Подразделение", max_length=255, unique=True)
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        verbose_name = "Подразделение"
        verbose_name_plural = "Подразделения"

    def __str__(self):
        return self.name


class Position(models.Model):
    name = models.CharField("Должность", max_length=255, unique=True)
    is_active = models.BooleanField("Активна", default=True)

    class Meta:
        verbose_name = "Должность"
        verbose_name_plural = "Должности"

    def __str__(self):
        return self.name


class User(AbstractUser):
    avatar = models.ImageField(
        upload_to="avatars/",
        null=True,
        blank=True,
        verbose_name="Аватар"
    )

    # Подразделение — выбор из справочника
    department = models.ForeignKey(
        Department,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Подразделение"
    )

    # Должность — либо из справочника
    position = models.ForeignKey(
        Position,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Должность"
    )

    # Либо кастомная должность (если выбрано «Другое»)
    custom_position = models.CharField(
        "Другая должность",
        max_length=255,
        null=True,
        blank=True
    )

    # Контакты (по ТЗ — без строгой валидации)
    telegram = models.CharField(
        "Telegram",
        max_length=255,
        null=True,
        blank=True
    )

    phone = models.CharField(
        "Телефон",
        max_length=50,
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def clean(self):
        """
        Соответствие ТЗ:
        либо position, либо custom_position — но не оба сразу
        """
        if self.position and self.custom_position:
            raise ValueError(
                "Нельзя указать должность и кастомную должность одновременно"
            )
