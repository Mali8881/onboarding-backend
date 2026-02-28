from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from accounts.models import Department, Role


class KBCategory(models.Model):
    name = models.CharField(max_length=150)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )

    class Meta:
        unique_together = ("name", "parent")
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class KBArticle(models.Model):
    class Visibility(models.TextChoices):
        ALL = "all", "All"
        DEPARTMENT = "department", "Department"
        ROLE = "role", "Role"

    title = models.CharField(max_length=255)
    content = models.TextField()
    category = models.ForeignKey(
        KBCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles",
    )
    tags = models.JSONField(default=list, blank=True)
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.ALL)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="kb_articles",
    )
    role_name = models.CharField(
        max_length=32,
        choices=Role.Name.choices,
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="kb_articles_created",
    )
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [
            models.Index(fields=["visibility"]),
            models.Index(fields=["is_published"]),
            models.Index(fields=["department"]),
            models.Index(fields=["role_name"]),
        ]

    def clean(self):
        if self.visibility == self.Visibility.DEPARTMENT and not self.department_id:
            raise ValidationError("Department visibility requires department.")
        if self.visibility == self.Visibility.ROLE and not self.role_name:
            raise ValidationError("Role visibility requires role_name.")
        if self.visibility != self.Visibility.DEPARTMENT:
            self.department = None
        if self.visibility != self.Visibility.ROLE:
            self.role_name = None

    def __str__(self):
        return self.title


class KBViewLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="kb_view_logs",
    )
    article = models.ForeignKey(
        KBArticle,
        on_delete=models.CASCADE,
        related_name="view_logs",
    )
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-viewed_at", "-id"]
        indexes = [
            models.Index(fields=["article", "viewed_at"]),
            models.Index(fields=["user", "viewed_at"]),
        ]
