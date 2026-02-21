from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import AuditLog, Role, User
from apps.attendance.models import AttendanceMark, WorkCalendarDay
from apps.payroll.models import PayrollEntry, PayrollPeriod, SalaryProfile


class PayrollApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.employee_role, _ = Role.objects.get_or_create(
            name=Role.Name.EMPLOYEE,
            defaults={"level": Role.Level.EMPLOYEE},
        )
        self.admin_role, _ = Role.objects.get_or_create(
            name=Role.Name.ADMIN,
            defaults={"level": Role.Level.ADMIN},
        )
        self.super_admin_role, _ = Role.objects.get_or_create(
            name=Role.Name.SUPER_ADMIN,
            defaults={"level": Role.Level.SUPER_ADMIN},
        )

        self.employee = User.objects.create_user(
            username="payroll_employee",
            password="StrongPass123!",
            role=self.employee_role,
        )
        self.other_employee = User.objects.create_user(
            username="payroll_employee2",
            password="StrongPass123!",
            role=self.employee_role,
        )
        self.admin = User.objects.create_user(
            username="payroll_admin",
            password="StrongPass123!",
            role=self.admin_role,
        )
        self.super_admin = User.objects.create_user(
            username="payroll_super_admin",
            password="StrongPass123!",
            role=self.super_admin_role,
        )

    def _seed_calendar_and_attendance(self):
        for day in range(1, 6):
            WorkCalendarDay.objects.create(
                date=date(2026, 3, day),
                is_working_day=True,
                is_holiday=False,
            )
        for day in (1, 2, 3):
            AttendanceMark.objects.create(
                user=self.employee,
                date=date(2026, 3, day),
                status=AttendanceMark.Status.PRESENT,
                created_by=self.employee,
            )

    def test_employee_cannot_access_payroll_admin_endpoints(self):
        self.client.force_authenticate(user=self.employee)
        response = self.client.get("/api/v1/payroll/admin/?year=2026&month=3")
        self.assertEqual(response.status_code, 403)

        response = self.client.post("/api/v1/payroll/admin/generate/", {"year": 2026, "month": 3}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_salary_profile(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/v1/payroll/admin/salary-profiles/",
            {
                "user": self.employee.id,
                "base_salary": "1000.00",
                "employment_type": "daily",
                "currency": "RUB",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(SalaryProfile.objects.filter(user=self.employee).exists())
        self.assertTrue(AuditLog.objects.filter(action="salary_profile_created").exists())

    def test_generate_period_is_idempotent_and_updates_entries(self):
        self._seed_calendar_and_attendance()
        SalaryProfile.objects.create(
            user=self.employee,
            base_salary="1000.00",
            employment_type=SalaryProfile.EmploymentType.DAILY,
            currency="RUB",
            is_active=True,
        )
        SalaryProfile.objects.create(
            user=self.other_employee,
            base_salary="1000.00",
            employment_type=SalaryProfile.EmploymentType.DAILY,
            currency="RUB",
            is_active=True,
        )

        self.client.force_authenticate(user=self.admin)
        first = self.client.post("/api/v1/payroll/admin/generate/", {"year": 2026, "month": 3}, format="json")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data["entries_created"], 4)
        self.assertEqual(first.data["entries_updated"], 0)

        second = self.client.post("/api/v1/payroll/admin/generate/", {"year": 2026, "month": 3}, format="json")
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data["entries_created"], 0)
        self.assertEqual(second.data["entries_updated"], 4)

        entry = PayrollEntry.objects.get(user=self.employee, period__year=2026, period__month=3)
        self.assertEqual(entry.planned_days, 5)
        self.assertEqual(entry.worked_days, 3)
        self.assertEqual(str(entry.salary_amount), "3000.00")
        self.assertEqual(str(entry.total_amount), "3000.00")
        self.assertTrue(AuditLog.objects.filter(action="payroll_period_generated").exists())

    def test_my_payroll_returns_only_own_entry(self):
        self._seed_calendar_and_attendance()
        SalaryProfile.objects.create(
            user=self.employee,
            base_salary="1000.00",
            employment_type=SalaryProfile.EmploymentType.DAILY,
            currency="RUB",
            is_active=True,
        )
        self.client.force_authenticate(user=self.admin)
        self.client.post("/api/v1/payroll/admin/generate/", {"year": 2026, "month": 3}, format="json")

        self.client.force_authenticate(user=self.employee)
        my = self.client.get("/api/v1/payroll/?year=2026&month=3")
        self.assertEqual(my.status_code, 200)
        self.assertEqual(my.data["user"], self.employee.id)

    def test_locked_period_blocks_regeneration(self):
        self._seed_calendar_and_attendance()
        self.client.force_authenticate(user=self.admin)
        self.client.post("/api/v1/payroll/admin/generate/", {"year": 2026, "month": 3}, format="json")
        period = PayrollPeriod.objects.get(year=2026, month=3)
        period.status = PayrollPeriod.Status.LOCKED
        period.save(update_fields=["status"])

        regen = self.client.post("/api/v1/payroll/admin/generate/", {"year": 2026, "month": 3}, format="json")
        self.assertEqual(regen.status_code, 409)

    def test_super_admin_can_change_period_status(self):
        self._seed_calendar_and_attendance()
        self.client.force_authenticate(user=self.admin)
        self.client.post("/api/v1/payroll/admin/generate/", {"year": 2026, "month": 3}, format="json")
        period = PayrollPeriod.objects.get(year=2026, month=3)

        self.client.force_authenticate(user=self.super_admin)
        response = self.client.patch(
            f"/api/v1/payroll/admin/periods/{period.id}/status/",
            {"status": "paid"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        period.refresh_from_db()
        self.assertEqual(period.status, PayrollPeriod.Status.PAID)
        self.assertTrue(AuditLog.objects.filter(action="payroll_period_status_changed").exists())

