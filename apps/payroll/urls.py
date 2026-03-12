from django.urls import path

from .views import (
    HourlyRateDetailAdminAPIView,
    HourlyRateAdminAPIView,
    HourlyRateHistoryAdminAPIView,
    PayrollAdminAPIView,
    PayrollAdminEmployeesAPIView,
    PayrollFundSummaryAPIView,
    PayrollMyAPIView,
    PayrollRecalculateAPIView,
    PayrollRecordStatusAPIView,
)


urlpatterns = [
    path("", PayrollMyAPIView.as_view(), name="payroll-my"),
    path("admin/", PayrollAdminAPIView.as_view(), name="payroll-admin"),
    path("admin/employees/", PayrollAdminEmployeesAPIView.as_view(), name="payroll-admin-employees"),
    path("admin/summary/", PayrollFundSummaryAPIView.as_view(), name="payroll-admin-summary"),
    path("admin/recalculate/", PayrollRecalculateAPIView.as_view(), name="payroll-recalculate"),
    path("admin/records/<int:record_id>/status/", PayrollRecordStatusAPIView.as_view(), name="payroll-record-status"),
    path("hourly-rates/", HourlyRateAdminAPIView.as_view(), name="payroll-hourly-rates-legacy"),
    path("admin/hourly-rates/", HourlyRateAdminAPIView.as_view(), name="payroll-hourly-rates"),
    path("hourly-rates/<int:user_id>/", HourlyRateDetailAdminAPIView.as_view(), name="payroll-hourly-rate-detail-legacy"),
    path("admin/hourly-rates/<int:user_id>/", HourlyRateDetailAdminAPIView.as_view(), name="payroll-hourly-rate-detail"),
    path("admin/hourly-rates/<int:user_id>/history/", HourlyRateHistoryAdminAPIView.as_view(), name="payroll-hourly-rates-history"),
    # Alias: frontend uses /salary-profiles/ but data comes from PayrollCompensation (formerly SalaryProfile)
    path("admin/salary-profiles/", HourlyRateAdminAPIView.as_view(), name="payroll-salary-profiles"),
]
