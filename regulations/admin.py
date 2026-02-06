from django.contrib import admin
from .models import Regulation


@admin.register(Regulation)
class RegulationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "type",
        "language",
        "is_active",
        "position",
    )
    list_filter = (
        "type",
        "language",
        "is_active",
    )
    search_fields = ("title",)
    ordering = ("position",)
