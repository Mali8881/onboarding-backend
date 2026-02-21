from django.apps import AppConfig


class AttendanceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.attendance"
    verbose_name = "Посещаемость"

    def ready(self):
        # Force admin registration for nested app path in case autodiscover misses it.
        try:
            import apps.attendance.admin  # noqa: F401
        except Exception:
            # Never block app startup on admin import.
            return

