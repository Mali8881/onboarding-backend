from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class WorkSchedule(models.Model):
    name = models.CharField(max_length=100)

    work_days = models.JSONField(
        help_text="Список рабочих дней недели (0=Пн ... 6=Вс)"
    )

    start_time = models.TimeField()
    end_time = models.TimeField()

    break_start = models.TimeField(null=True, blank=True)
    break_end = models.TimeField(null=True, blank=True)

    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "График работы"
        verbose_name_plural = "Графики работы"
        indexes = [
            models.Index(fields=["is_active"]),
        ]

    def clean(self):
        if not isinstance(self.work_days, list):
            raise ValidationError("work_days должен быть списком")

        for day in self.work_days:
            if not isinstance(day, int) or day < 0 or day > 6:
                raise ValidationError("work_days может содержать только числа от 0 до 6")

        if self.is_default:
            exists_default = WorkSchedule.objects.exclude(pk=self.pk).filter(is_default=True).exists()
            if exists_default:
                raise ValidationError("Может быть только один график по умолчанию")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ProductionCalendar(models.Model):
    date = models.DateField(unique=True)
    is_working_day = models.BooleanField(default=True)
    is_holiday = models.BooleanField(default=False)
    holiday_name = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = "Производственный день (РФ)"
        verbose_name_plural = "Производственный календарь (РФ)"
        ordering = ["date"]
        indexes = [
            models.Index(fields=["date"]),
        ]

    def clean(self):
        if self.is_holiday and self.is_working_day:
            raise ValidationError("День не может быть одновременно рабочим и праздничным")

    def __str__(self):
        return f"{self.date}"


class UserWorkSchedule(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="work_schedule",
    )

    schedule = models.ForeignKey(
        WorkSchedule,
        on_delete=models.CASCADE,
        related_name="users",
    )

    approved = models.BooleanField(default=True)
    requested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "График пользователя"
        verbose_name_plural = "Графики пользователей"
        indexes = [
            models.Index(fields=["approved"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.schedule}"
