from django.contrib import admin
from .models import SystemLog


@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "level")
    list_filter = ("level", "created_at")
    search_fields = ("action", "actor__email")
    readonly_fields = (
        "id",
        "actor",
        "action",
        "level",
        "metadata",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
