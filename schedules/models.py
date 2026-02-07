import uuid
from django.db import models


class WorkSchedule(models.Model):
    """
    Типовой график работы
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    # структура графика (пример: JSON)
    structure = models.JSONField(
        help_text="Описание рабочих дней и часов"
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
