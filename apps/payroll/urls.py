from django.urls import path

from .views import (
    HourlyRateAdminAPIView,
    HourlyRateHistoryAdminAPIView,
    PayrollAdminAPIView,
    PayrollFundSummaryAPIView,
    PayrollMyAPIView,
    PayrollRecalculateAPIView,
    PayrollRecordStatusAPIView,
)


urlpatterns = [
    path("", PayrollMyAPIView.as_view(), name="payroll-my"),
    path("admin/", PayrollAdminAPIView.as_view(), name="payroll-admin"),
    path("admin/summary/", PayrollFundSummaryAPIView.as_view(), name="payroll-admin-summary"),
    path("admin/recalculate/", PayrollRecalculateAPIView.as_view(), name="payroll-recalculate"),
    path("admin/records/<int:record_id>/status/", PayrollRecordStatusAPIView.as_view(), name="payroll-record-status"),
    path("admin/hourly-rates/", HourlyRateAdminAPIView.as_view(), name="payroll-hourly-rates"),
    path("admin/hourly-rates/<int:user_id>/history/", HourlyRateHistoryAdminAPIView.as_view(), name="payroll-hourly-rates-history"),
]
