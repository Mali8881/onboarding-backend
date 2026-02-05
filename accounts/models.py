import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models

class Department(models.Model):
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    class Meta:
        verbose_name = "Department"
        verbose_name_plural = "Departments"
    def __str__(self):
        return self.name

class Position(models.Model):
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    class Meta:
        verbose_name = "Position"
        verbose_name_plural = "Positions"
    def __str__(self):
        return self.name

class User(AbstractUser):
    # КЛАСС ROLE ДОЛЖЕН БЫТЬ ТУТ
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Администратор'
        SUPER_ADMIN = 'super_admin', 'Супер-администратор'
        USER = 'user', 'Пользователь'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.USER,
        verbose_name="Роль"
    )
    full_name = models.CharField(max_length=255, blank=True)
    photo = models.ImageField(upload_to="users/photos/", blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    telegram = models.CharField(max_length=100, blank=True, null=True)
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL)
    position = models.ForeignKey(Position, null=True, blank=True, on_delete=models.SET_NULL)
    language = models.CharField(max_length=10, default="ru")

    def __str__(self):
        return self.username

