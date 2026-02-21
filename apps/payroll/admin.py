from django.contrib import admin

from .models import PayrollEntry, PayrollPeriod, SalaryProfile


@admin.register(SalaryProfile)
class SalaryProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "base_salary", "employment_type", "currency", "is_active")
    list_filter = ("employment_type", "is_active", "currency")
    search_fields = ("user__username",)


@admin.register(PayrollPeriod)
class PayrollPeriodAdmin(admin.ModelAdmin):
    list_display = ("year", "month", "status", "created_at")
    list_filter = ("status", "year", "month")
    search_fields = ("year", "month")


@admin.register(PayrollEntry)
class PayrollEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "period", "planned_days", "worked_days", "salary_amount", "total_amount")
    list_filter = ("period__year", "period__month")
    search_fields = ("user__username",)

