import uuid
from django.db import models
from django.conf import settings


class WorkSchedule(models.Model):
    """
    Типовой график работы (5/2, 2/2 и т.д.)
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    name = models.CharField(
        max_length=255,
        verbose_name="Название"
    )

    work_days = models.JSONField(
        verbose_name="Рабочие дни"
    )
    # пример: [0,1,2,3,4]

    start_time = models.TimeField(
        verbose_name="Начало"
    )

    end_time = models.TimeField(
        verbose_name="Конец"
    )

    break_time = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Перерыв"
    )
    # пример: {"start": "13:00", "end": "14:00"}

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
    Производственный календарь РФ
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
        verbose_name="Праздничный день"
    )

    class Meta:
        verbose_name = "Производственный день"
        verbose_name_plural = "Производственный календарь"

    def __str__(self):
        return str(self.date)


class UserWorkSchedule(models.Model):
    """
    График конкретного пользователя (с согласованием)
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

    approved = models.BooleanField(
        default=False,
        verbose_name="Согласован"
    )

    class Meta:
        verbose_name = "График пользователя"
        verbose_name_plural = "Графики пользователей"

    def __str__(self):
        return f"{self.user} → {self.schedule}"
