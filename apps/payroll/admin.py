from django.contrib import admin

from .models import PayrollEntry, PayrollPeriod, SalaryProfile


@admin.register(SalaryProfile)
class SalaryProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "base_salary", "employment_type", "currency", "is_active")
    list_filter = ("employment_type", "is_active", "currency")
    search_fields = ("user__username",)
    autocomplete_fields = ("user",)
    fieldsets = (
        ("Сотрудник", {"fields": ("user",)}),
        ("Условия оплаты", {"fields": ("employment_type", "base_salary", "currency", "is_active")}),
    )


@admin.register(PayrollPeriod)
class PayrollPeriodAdmin(admin.ModelAdmin):
    list_display = ("year", "month", "status", "created_at")
    list_filter = ("status", "year", "month")
    search_fields = ("year", "month")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Период", {"fields": ("year", "month", "status")}),
        ("Системные поля", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(PayrollEntry)
class PayrollEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "period", "planned_days", "worked_days", "salary_amount", "total_amount")
    list_filter = ("period__year", "period__month")
    search_fields = ("user__username",)
    autocomplete_fields = ("user", "period")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Связи", {"fields": ("user", "period")}),
        ("Расчет", {"fields": ("planned_days", "worked_days", "advances", "salary_amount", "total_amount")}),
        ("Системные поля", {"fields": ("created_at", "updated_at")}),
    )
