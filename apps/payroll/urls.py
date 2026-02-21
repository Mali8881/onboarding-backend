from django.urls import path

from .views import (
    PayrollAdminAPIView,
    PayrollGenerateAPIView,
    PayrollMyAPIView,
    PayrollPeriodStatusAPIView,
    SalaryProfileAdminAPIView,
    SalaryProfileAdminDetailAPIView,
)


urlpatterns = [
    path("", PayrollMyAPIView.as_view(), name="payroll-my"),
    path("admin/", PayrollAdminAPIView.as_view(), name="payroll-admin"),
    path("admin/generate/", PayrollGenerateAPIView.as_view(), name="payroll-generate"),
    path("admin/periods/<int:period_id>/status/", PayrollPeriodStatusAPIView.as_view(), name="payroll-period-status"),
    path("admin/salary-profiles/", SalaryProfileAdminAPIView.as_view(), name="salary-profile-admin"),
    path("admin/salary-profiles/<int:profile_id>/", SalaryProfileAdminDetailAPIView.as_view(), name="salary-profile-admin-detail"),
]

