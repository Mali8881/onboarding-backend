from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils import timezone
import uuid

from .managers import  UserManager
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator


def validate_photo_size(value):
    max_size = 2 * 1024 * 1024  # 2MB
    if value.size > max_size:
        raise ValidationError("Максимальный размер фото — 2MB.")

# ================= RBAC =================
class Permission(models.Model):
    code = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.code


class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(Permission, blank=True)

    def __str__(self):
        return self.name

# ================= Reference Tables =================

class Department(models.Model):
    name = models.CharField(max_length=150, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Position(models.Model):
    name = models.CharField(max_length=150, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


# ================= User =================
class User(AbstractUser):
    role = models.ForeignKey(Role, on_delete=models.PROTECT)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, blank=True)

    custom_position = models.CharField(max_length=150, blank=True)

    telegram = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    photo = models.ImageField(
        upload_to="users/",
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"]),
            validate_photo_size
        ]
    )

    objects = UserManager()

    is_blocked = models.BooleanField(default=False)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    lockout_until = models.DateTimeField(null=True, blank=True)

    def has_permission(self, code: str) -> bool:
        """
        Проверка наличия permission по коду.
        """
        if not self.is_authenticated:
            return False

        if not self.role:
            return False

        return self.role.permissions.filter(code=code).exists()

    def has_any_permission(self, codes: list[str]) -> bool:
        """
        Проверка наличия хотя бы одного permission.
        """
        if not self.is_authenticated or not self.role:
            return False

        return self.role.permissions.filter(code__in=codes).exists()

    def has_all_permissions(self, codes: list[str]) -> bool:
        """
        Проверка наличия всех permission.
        """
        if not self.is_authenticated or not self.role:
            return False

        user_codes = set(self.role.permissions.values_list("code", flat=True))
        return set(codes).issubset(user_codes)

def has_permission(self, code: str) -> bool:
    if not self.is_authenticated:
        return False

    if not self.role:
        return False

    return self.role.permissions.filter(code=code).exists()





# ================= Security =================

class AuditLog(models.Model):

    class Level(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        ERROR = "error", "Error"
        CRITICAL = "critical", "Critical"

    class Category(models.TextChoices):
        AUTH = "auth", "Authentication"
        USER = "user", "User management"
        SECURITY = "security", "Security"
        CONTENT = "content", "Content"
        SYSTEM = "system", "System"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    action = models.CharField(max_length=255)
    object_type = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=100, blank=True)

    level = models.CharField(
        max_length=20,
        choices=Level.choices,
        default=Level.INFO
    )

    category = models.CharField(
        max_length=50,
        choices=Category.choices,
        default=Category.SYSTEM
    )

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["level"]),
            models.Index(fields=["category"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["user"]),
        ]

    @classmethod
    def log(
        cls,
        action,
        user=None,
        object_type="",
        object_id="",
        level=Level.INFO,
        category=Category.SYSTEM,
        ip_address=None,
    ):
        return cls.objects.create(
            user=user,
            action=action,
            object_type=object_type,
            object_id=object_id,
            level=level,
            category=category,
            ip_address=ip_address,
        )

    def __str__(self):
        return f"[{self.level.upper()}] {self.action}"


class LoginHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    success = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
class PasswordResetToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() > self.created_at + timezone.timedelta(hours=24)


class UserSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    expires_at = models.DateTimeField()
class TwoFactorCode(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.created_at + timedelta(minutes=5)
