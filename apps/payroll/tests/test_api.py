from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import AuditLog, Department, Role, User
from apps.attendance.models import AttendanceMark
from apps.payroll.models import HourlyRateHistory, PayrollRecord


class PayrollApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.employee_role, _ = Role.objects.get_or_create(
            name=Role.Name.EMPLOYEE,
            defaults={"level": Role.Level.EMPLOYEE},
        )
        self.intern_role, _ = Role.objects.get_or_create(
            name=Role.Name.INTERN,
            defaults={"level": Role.Level.INTERN},
        )
        self.admin_role, _ = Role.objects.get_or_create(
            name=Role.Name.ADMIN,
            defaults={"level": Role.Level.ADMIN},
        )
        self.administrator_role, _ = Role.objects.get_or_create(
            name=Role.Name.ADMINISTRATOR,
            defaults={"level": Role.Level.ADMINISTRATOR},
        )
        self.super_admin_role, _ = Role.objects.get_or_create(
            name=Role.Name.SUPER_ADMIN,
            defaults={"level": Role.Level.SUPER_ADMIN},
        )
        self.dept_sales = Department.objects.create(name="Sales")
        self.dept_marketing = Department.objects.create(name="Marketing")

        self.employee = User.objects.create_user(
            username="payroll_employee",
            password="StrongPass123!",
            role=self.employee_role,
            department=self.dept_sales,
            current_hourly_rate=Decimal("100.00"),
        )
        self.other_employee = User.objects.create_user(
            username="payroll_employee2",
            password="StrongPass123!",
            role=self.employee_role,
            department=self.dept_marketing,
            current_hourly_rate=Decimal("120.00"),
        )
        self.intern = User.objects.create_user(
            username="payroll_intern",
            password="StrongPass123!",
            role=self.intern_role,
            department=self.dept_sales,
            current_hourly_rate=Decimal("90.00"),
        )
        self.admin = User.objects.create_user(
            username="payroll_admin",
            password="StrongPass123!",
            role=self.admin_role,
            department=self.dept_sales,
            current_hourly_rate=Decimal("150.00"),
        )
        self.super_admin = User.objects.create_user(
            username="payroll_super_admin",
            password="StrongPass123!",
            role=self.super_admin_role,
            current_hourly_rate=Decimal("200.00"),
        )
        self.administrator = User.objects.create_user(
            username="payroll_administrator",
            password="StrongPass123!",
            role=self.administrator_role,
            current_hourly_rate=Decimal("180.00"),
        )

    def _seed_employee_hours(self):
        AttendanceMark.objects.create(
            user=self.employee,
            date=date(2026, 3, 1),
            status=AttendanceMark.Status.PRESENT,
            actual_hours=Decimal("8.00"),
            planned_hours=Decimal("8.00"),
            created_by=self.employee,
        )
        AttendanceMark.objects.create(
            user=self.employee,
            date=date(2026, 3, 2),
            status=AttendanceMark.Status.REMOTE,
            actual_hours=Decimal("6.00"),
            planned_hours=Decimal("8.00"),
            created_by=self.employee,
        )

    def test_admin_has_department_view_access_and_limited_edit_access(self):
        self.client.force_authenticate(user=self.employee)
        response = self.client.post("/api/v1/payroll/admin/recalculate/", {"year": 2026, "month": 3}, format="json")
        self.assertEqual(response.status_code, 403)

        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/v1/payroll/admin/?year=2026&month=3")
        self.assertEqual(response.status_code, 200)
        summary = self.client.get("/api/v1/payroll/admin/summary/?year=2026&month=3")
        self.assertEqual(summary.status_code, 200)
        rates = self.client.get("/api/v1/payroll/admin/hourly-rates/")
        self.assertEqual(rates.status_code, 200)
        returned_user_ids = {row["user"] for row in rates.data}
        self.assertIn(self.employee.id, returned_user_ids)
        self.assertNotIn(self.other_employee.id, returned_user_ids)
        self.assertNotIn(self.admin.id, returned_user_ids)
        self.assertNotIn(self.intern.id, returned_user_ids)
        history = self.client.get(f"/api/v1/payroll/admin/hourly-rates/{self.employee.id}/history/")
        self.assertEqual(history.status_code, 200)

        can_set_rate_own_department = self.client.post(
            "/api/v1/payroll/admin/hourly-rates/",
            {"user_id": self.employee.id, "rate": "250.00", "start_date": "2026-03-10"},
            format="json",
        )
        self.assertEqual(can_set_rate_own_department.status_code, 200)
        cannot_set_rate_other_department = self.client.post(
            "/api/v1/payroll/admin/hourly-rates/",
            {"user_id": self.other_employee.id, "rate": "250.00", "start_date": "2026-03-10"},
            format="json",
        )
        self.assertEqual(cannot_set_rate_other_department.status_code, 403)
        cannot_set_rate_for_self = self.client.post(
            "/api/v1/payroll/admin/hourly-rates/",
            {"user_id": self.admin.id, "rate": "250.00", "start_date": "2026-03-10"},
            format="json",
        )
        self.assertEqual(cannot_set_rate_for_self.status_code, 403)
        cannot_set_rate_for_intern = self.client.post(
            "/api/v1/payroll/admin/hourly-rates/",
            {"user_id": self.intern.id, "rate": "250.00", "start_date": "2026-03-10"},
            format="json",
        )
        self.assertEqual(cannot_set_rate_for_intern.status_code, 403)
        cannot_recalculate = self.client.post(
            "/api/v1/payroll/admin/recalculate/",
            {"year": 2026, "month": 3},
            format="json",
        )
        self.assertEqual(cannot_recalculate.status_code, 403)

        self.client.force_authenticate(user=self.intern)
        response = self.client.get("/api/v1/payroll/admin/summary/?year=2026&month=3")
        self.assertEqual(response.status_code, 403)

    def test_administrator_can_manage_payroll_admin_endpoints(self):
        self.client.force_authenticate(user=self.administrator)
        response = self.client.get("/api/v1/payroll/admin/?year=2026&month=3")
        self.assertEqual(response.status_code, 200)
        cannot_set_rate_for_self = self.client.post(
            "/api/v1/payroll/admin/hourly-rates/",
            {"user_id": self.administrator.id, "rate": "250.00", "start_date": "2026-03-10"},
            format="json",
        )
        self.assertEqual(cannot_set_rate_for_self.status_code, 403)

    def test_superadmin_can_set_hourly_rate_and_see_history(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.post(
            "/api/v1/payroll/admin/hourly-rates/",
            {"user_id": self.employee.id, "rate": "250.00", "start_date": "2026-03-10"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.employee.refresh_from_db()
        self.assertEqual(str(self.employee.current_hourly_rate), "250.00")
        self.assertTrue(HourlyRateHistory.objects.filter(user=self.employee, start_date=date(2026, 3, 10)).exists())

        history = self.client.get(f"/api/v1/payroll/admin/hourly-rates/{self.employee.id}/history/")
        self.assertEqual(history.status_code, 200)
        self.assertGreaterEqual(len(history.data), 1)
        self.assertTrue(AuditLog.objects.filter(action="hourly_rate_changed").exists())
        cannot_set_rate_for_self = self.client.post(
            "/api/v1/payroll/admin/hourly-rates/",
            {"user_id": self.super_admin.id, "rate": "260.00", "start_date": "2026-03-11"},
            format="json",
        )
        self.assertEqual(cannot_set_rate_for_self.status_code, 403)

    def test_recalculate_uses_actual_hours_and_current_rate(self):
        self._seed_employee_hours()
        self.client.force_authenticate(user=self.super_admin)

        response = self.client.post("/api/v1/payroll/admin/recalculate/", {"year": 2026, "month": 3}, format="json")
        self.assertEqual(response.status_code, 200)

        record = PayrollRecord.objects.get(user=self.employee, month=date(2026, 3, 1))
        self.assertEqual(str(record.total_hours), "14.00")
        self.assertEqual(str(record.total_salary), "1400.00")
        self.assertEqual(record.status, PayrollRecord.Status.CALCULATED)

    def test_recalculate_splits_salary_when_rate_changes_mid_month(self):
        AttendanceMark.objects.create(
            user=self.employee,
            date=date(2026, 3, 5),
            status=AttendanceMark.Status.PRESENT,
            actual_hours=Decimal("10.00"),
            planned_hours=Decimal("10.00"),
            created_by=self.employee,
        )
        AttendanceMark.objects.create(
            user=self.employee,
            date=date(2026, 3, 20),
            status=AttendanceMark.Status.PRESENT,
            actual_hours=Decimal("10.00"),
            planned_hours=Decimal("10.00"),
            created_by=self.employee,
        )

        HourlyRateHistory.objects.create(user=self.employee, rate=Decimal("100.00"), start_date=date(2026, 3, 1))
        HourlyRateHistory.objects.create(user=self.employee, rate=Decimal("200.00"), start_date=date(2026, 3, 15))
        self.employee.current_hourly_rate = Decimal("200.00")
        self.employee.save(update_fields=["current_hourly_rate"])

        self.client.force_authenticate(user=self.super_admin)
        self.client.post("/api/v1/payroll/admin/recalculate/", {"year": 2026, "month": 3}, format="json")

        record = PayrollRecord.objects.get(user=self.employee, month=date(2026, 3, 1))
        self.assertEqual(str(record.total_hours), "20.00")
        self.assertEqual(str(record.total_salary), "3000.00")

    def test_can_set_minute_rate_and_recalculate(self):
        AttendanceMark.objects.create(
            user=self.employee,
            date=date(2026, 3, 6),
            status=AttendanceMark.Status.PRESENT,
            actual_hours=Decimal("2.00"),
            planned_hours=Decimal("2.00"),
            created_by=self.employee,
        )
        self.client.force_authenticate(user=self.super_admin)
        set_rate = self.client.post(
            "/api/v1/payroll/admin/hourly-rates/",
            {"user_id": self.employee.id, "pay_type": "minute", "minute_rate": "2.00"},
            format="json",
        )
        self.assertEqual(set_rate.status_code, 200)
        self.client.post("/api/v1/payroll/admin/recalculate/", {"year": 2026, "month": 3}, format="json")
        record = PayrollRecord.objects.get(user=self.employee, month=date(2026, 3, 1))
        self.assertEqual(str(record.total_salary), "240.00")

    def test_can_set_fixed_salary_and_recalculate(self):
        self.client.force_authenticate(user=self.super_admin)
        set_salary = self.client.post(
            "/api/v1/payroll/admin/hourly-rates/",
            {"user_id": self.employee.id, "pay_type": "fixed_salary", "fixed_salary": "5000.00"},
            format="json",
        )
        self.assertEqual(set_salary.status_code, 200)
        self.client.post("/api/v1/payroll/admin/recalculate/", {"year": 2026, "month": 3}, format="json")
        record = PayrollRecord.objects.get(user=self.employee, month=date(2026, 3, 1))
        self.assertEqual(str(record.total_salary), "5000.00")

    def test_no_attendance_means_zero_salary_for_non_intern(self):
        self.client.force_authenticate(user=self.super_admin)
        self.client.post("/api/v1/payroll/admin/recalculate/", {"year": 2026, "month": 3}, format="json")
        record = PayrollRecord.objects.get(user=self.other_employee, month=date(2026, 3, 1))
        self.assertEqual(str(record.total_hours), "0.00")
        self.assertEqual(str(record.total_salary), "0.00")
        self.assertFalse(PayrollRecord.objects.filter(user=self.intern, month=date(2026, 3, 1)).exists())

    def test_user_sees_only_own_salary(self):
        self._seed_employee_hours()
        self.client.force_authenticate(user=self.super_admin)
        self.client.post("/api/v1/payroll/admin/recalculate/", {"year": 2026, "month": 3}, format="json")

        self.client.force_authenticate(user=self.employee)
        my = self.client.get("/api/v1/payroll/?year=2026&month=3")
        self.assertEqual(my.status_code, 200)
        self.assertEqual(my.data["user"], self.employee.id)

        self.client.force_authenticate(user=self.admin)
        own = self.client.get("/api/v1/payroll/?year=2026&month=3")
        self.assertEqual(own.status_code, 200)
        self.assertEqual(own.data["user"], self.admin.id)

    def test_my_salary_returns_single_row_even_when_not_calculated_yet(self):
        self.client.force_authenticate(user=self.employee)
        response = self.client.get("/api/v1/payroll/?year=2026&month=4")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"], self.employee.id)
        self.assertEqual(str(response.data["total_hours"]), "0.00")
        self.assertEqual(str(response.data["total_salary"]), "0.00")

    def test_intern_cannot_access_my_salary_page(self):
        self.client.force_authenticate(user=self.intern)
        response = self.client.get("/api/v1/payroll/?year=2026&month=4")
        self.assertEqual(response.status_code, 403)

    def test_superadmin_can_mark_record_as_paid(self):
        self._seed_employee_hours()
        self.client.force_authenticate(user=self.super_admin)
        self.client.post("/api/v1/payroll/admin/recalculate/", {"year": 2026, "month": 3}, format="json")
        record = PayrollRecord.objects.get(user=self.employee, month=date(2026, 3, 1))

        response = self.client.patch(
            f"/api/v1/payroll/admin/records/{record.id}/status/",
            {"status": "paid"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        record.refresh_from_db()
        self.assertEqual(record.status, PayrollRecord.Status.PAID)
        self.assertIsNotNone(record.paid_at)
        self.assertTrue(AuditLog.objects.filter(action="payroll_period_status_changed").exists())

    def test_superadmin_can_view_payroll_fund_summary(self):
        self._seed_employee_hours()
        self.client.force_authenticate(user=self.super_admin)
        self.client.post("/api/v1/payroll/admin/recalculate/", {"year": 2026, "month": 3}, format="json")
        summary = self.client.get("/api/v1/payroll/admin/summary/?year=2026&month=3")
        self.assertEqual(summary.status_code, 200)
        self.assertIn("payroll_fund", summary.data)
        self.assertIn("average_salary", summary.data)
        self.assertIn("total_employees", summary.data)
        self.assertIn("total_hours", summary.data)
