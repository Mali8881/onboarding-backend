import uuid
from django.db import models

from config import settings


class WorkSchedule(models.Model):
    """
    Типовой график работы (5/2, 2/2 и т.д.)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(
        max_length=255,
        verbose_name="Название"
    )

    # пример: [0,1,2,3,4] (Пн–Пт)
    work_days = models.JSONField(
        verbose_name="Рабочие дни"
    )

    start_time = models.TimeField(
        verbose_name="Начало рабочего дня"
    )

    end_time = models.TimeField(
        verbose_name="Конец рабочего дня"
    )

    # обеденный перерыв (основной)
    break_start = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Начало перерыва"
    )

    break_end = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Конец перерыва"
    )

    is_default = models.BooleanField(
        default=False,
        verbose_name="Базовый график компании"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Активен"
    )

    class Meta:
        verbose_name = "График работы"
        verbose_name_plural = "Графики работы"

    def __str__(self):
        return self.name
class ProductionCalendar(models.Model):
    """
    Производственный календарь Кыргызстана
    """
    date = models.DateField(
        unique=True,
        verbose_name="Дата"
    )

    is_working_day = models.BooleanField(
        verbose_name="Рабочий день"
    )

    is_holiday = models.BooleanField(
        default=False,
        verbose_name="Официальный праздник"
    )

    holiday_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Название праздника"
    )

    class Meta:
        verbose_name = "Производственный день (КР)"
        verbose_name_plural = "Производственный календарь (КР)"
        ordering = ["date"]

    def clean(self):
        # день не может быть одновременно рабочим и праздничным
        if self.is_working_day and self.is_holiday:
            raise ValueError(
                "День не может быть рабочим и праздничным одновременно"
            )

    def __str__(self):
        if self.is_holiday:
            return f"{self.date} — {self.holiday_name}"
        return str(self.date)


class UserWorkSchedule(models.Model):
    """
    График, выбранный пользователем
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="Пользователь"
    )

    schedule = models.ForeignKey(
        WorkSchedule,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="График"
    )

    class Meta:
        verbose_name = "График пользователя"
        verbose_name_plural = "Графики пользователей"

    def __str__(self):
        return f"{self.user} → {self.schedule}"