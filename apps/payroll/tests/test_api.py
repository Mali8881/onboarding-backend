from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Department, Role, User
from apps.payroll.models import PayrollCompensation, PayrollRecord


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

    def _recalculate(self):
        self.client.force_authenticate(user=self.super_admin)
        return self.client.post("/api/v1/payroll/admin/recalculate/", {"year": 2026, "month": 3}, format="json")

    def test_summary_contains_total_fund_alias(self):
        self._recalculate()
        summary = self.client.get("/api/v1/payroll/admin/summary/?year=2026&month=3")
        self.assertEqual(summary.status_code, 200)
        self.assertIn("payroll_fund", summary.data)
        self.assertIn("total_fund", summary.data)
        self.assertEqual(str(summary.data["payroll_fund"]), str(summary.data["total_fund"]))

    def test_my_payroll_returns_stable_contract_and_is_calculated_flag(self):
        self.client.force_authenticate(user=self.employee)
        response = self.client.get("/api/v1/payroll/?year=2026&month=4")
        self.assertEqual(response.status_code, 200)

        expected_fields = {
            "id",
            "user",
            "username",
            "month",
            "total_hours",
            "total_salary",
            "bonus",
            "status",
            "calculated_at",
            "paid_at",
            "is_calculated",
        }
        self.assertTrue(expected_fields.issubset(set(response.data.keys())))
        self.assertEqual(response.data["user"], self.employee.id)
        self.assertFalse(response.data["is_calculated"])

        self._recalculate()
        response2 = self.client.get("/api/v1/payroll/?year=2026&month=3")
        self.assertEqual(response2.status_code, 200)
        self.assertTrue(response2.data["is_calculated"])

    def test_admin_list_returns_stable_contract(self):
        self._recalculate()
        response = self.client.get("/api/v1/payroll/admin/?year=2026&month=3")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 1)

        expected_fields = {
            "id",
            "user",
            "username",
            "month",
            "total_hours",
            "total_salary",
            "bonus",
            "status",
            "calculated_at",
            "paid_at",
        }
        self.assertTrue(expected_fields.issubset(set(response.data[0].keys())))

    def test_hourly_rates_post_accepts_contract_pay_types(self):
        self.client.force_authenticate(user=self.super_admin)

        hourly = self.client.post(
            "/api/v1/payroll/admin/hourly-rates/",
            {"user_id": self.employee.id, "pay_type": "hourly", "hourly_rate": "250.00"},
            format="json",
        )
        self.assertEqual(hourly.status_code, 200)

        minute = self.client.post(
            "/api/v1/payroll/admin/hourly-rates/",
            {"user_id": self.employee.id, "pay_type": "minute", "minute_rate": "2.50"},
            format="json",
        )
        self.assertEqual(minute.status_code, 200)

        fixed = self.client.post(
            "/api/v1/payroll/admin/hourly-rates/",
            {"user_id": self.employee.id, "pay_type": "fixed_salary", "fixed_salary": "5000.00"},
            format="json",
        )
        self.assertEqual(fixed.status_code, 200)

    def test_hourly_rates_invalid_payload_returns_field_errors(self):
        self.client.force_authenticate(user=self.super_admin)

        missing_fixed_salary = self.client.post(
            "/api/v1/payroll/admin/hourly-rates/",
            {"user_id": self.employee.id, "pay_type": "fixed_salary"},
            format="json",
        )
        self.assertEqual(missing_fixed_salary.status_code, 400)
        self.assertIn("fixed_salary", missing_fixed_salary.data)

        invalid_legacy_pay_type = self.client.post(
            "/api/v1/payroll/admin/hourly-rates/",
            {"user_id": self.employee.id, "pay_type": "fixed", "fixed_salary": "1000.00"},
            format="json",
        )
        self.assertEqual(invalid_legacy_pay_type.status_code, 400)
        self.assertIn("pay_type", invalid_legacy_pay_type.data)

    def test_recalculate_applies_compensation_without_attendance(self):
        self.client.force_authenticate(user=self.super_admin)
        self.client.post(
            "/api/v1/payroll/admin/hourly-rates/",
            {"user_id": self.employee.id, "pay_type": "hourly", "hourly_rate": "100.00"},
            format="json",
        )
        self.client.post(
            "/api/v1/payroll/admin/hourly-rates/",
            {"user_id": self.other_employee.id, "pay_type": "fixed_salary", "fixed_salary": "5000.00"},
            format="json",
        )
        self.client.post(
            "/api/v1/payroll/admin/hourly-rates/",
            {"user_id": self.admin.id, "pay_type": "minute", "minute_rate": "2.00"},
            format="json",
        )

        recalc = self._recalculate()
        self.assertEqual(recalc.status_code, 200)

        employee_record = PayrollRecord.objects.get(user=self.employee, month=date(2026, 3, 1))
        self.assertEqual(str(employee_record.total_hours), "160.00")
        self.assertEqual(str(employee_record.total_salary), "16000.00")

        other_record = PayrollRecord.objects.get(user=self.other_employee, month=date(2026, 3, 1))
        self.assertEqual(str(other_record.total_hours), "0.00")
        self.assertEqual(str(other_record.total_salary), "5000.00")

        admin_record = PayrollRecord.objects.get(user=self.admin, month=date(2026, 3, 1))
        self.assertEqual(str(admin_record.total_hours), "160.00")
        self.assertEqual(str(admin_record.total_salary), "19200.00")

        self.assertFalse(PayrollRecord.objects.filter(user=self.intern, month=date(2026, 3, 1)).exists())

    def test_intern_cannot_access_my_payroll(self):
        self.client.force_authenticate(user=self.intern)
        response = self.client.get("/api/v1/payroll/?year=2026&month=3")
        self.assertEqual(response.status_code, 403)

    def test_self_edit_compensation_is_forbidden(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.post(
            "/api/v1/payroll/admin/hourly-rates/",
            {"user_id": self.super_admin.id, "pay_type": "hourly", "hourly_rate": "300.00"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("detail", response.data)

    def test_payroll_compensation_uses_only_contract_pay_type_values(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.post(
            "/api/v1/payroll/admin/hourly-rates/",
            {"user_id": self.employee.id, "pay_type": "salary", "fixed_salary": "1000.00"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("pay_type", response.data)

    def test_compensation_get_returns_contract_fields(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.get("/api/v1/payroll/admin/hourly-rates/")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 1)
        expected = {"user", "username", "role", "pay_type", "hourly_rate", "minute_rate", "fixed_salary"}
        self.assertTrue(expected.issubset(set(response.data[0].keys())))

        # keep model import used to avoid lint complaints in strict environments
        self.assertTrue(PayrollCompensation.objects.count() >= 0)
