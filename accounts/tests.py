from django.test import TestCase
from rest_framework.test import APIClient

from .models import Department, PasswordResetToken, Position, Role, User


class PasswordResetApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.role, _ = Role.objects.get_or_create(
            name=Role.Name.EMPLOYEE,
            defaults={"level": Role.Level.EMPLOYEE},
        )
        self.user = User.objects.create_user(
            username="employee1",
            email="employee1@example.com",
            password="OldPass123!",
            role=self.role,
        )

    def test_request_creates_token_for_existing_user(self):
        response = self.client.post(
            "/api/v1/accounts/password-reset/request/",
            {"username_or_email": "employee1"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(PasswordResetToken.objects.filter(user=self.user).exists())

    def test_confirm_resets_password(self):
        token = PasswordResetToken.objects.create(user=self.user)

        response = self.client.post(
            "/api/v1/accounts/password-reset/confirm/",
            {"token": str(token.token), "new_password": "NewPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPass123!"))

        token.refresh_from_db()
        self.assertTrue(token.is_used)


class OrgApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.role_admin = Role.objects.create(name=Role.Name.ADMIN, level=Role.Level.ADMIN)
        self.role_employee = Role.objects.create(
            name=Role.Name.EMPLOYEE, level=Role.Level.EMPLOYEE
        )

        self.admin = User.objects.create_user(
            username="org_admin",
            password="StrongPass123!",
            role=self.role_admin,
        )
        self.employee = User.objects.create_user(
            username="org_employee",
            password="StrongPass123!",
            role=self.role_employee,
        )

    def test_admin_can_create_department_with_parent(self):
        self.client.force_authenticate(self.admin)
        parent = Department.objects.create(name="IT", is_active=True)
        response = self.client.post(
            "/api/v1/accounts/org/departments/",
            {"name": "Backend", "parent": parent.id, "is_active": True},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["parent"], parent.id)

    def test_employee_cannot_create_department(self):
        self.client.force_authenticate(self.employee)
        response = self.client.post(
            "/api/v1/accounts/org/departments/",
            {"name": "Forbidden"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_cannot_delete_department_with_users(self):
        self.client.force_authenticate(self.admin)
        dept = Department.objects.create(name="Sales", is_active=True)
        self.employee.department = dept
        self.employee.save(update_fields=["department"])
        response = self.client.delete(f"/api/v1/accounts/org/departments/{dept.id}/")
        self.assertEqual(response.status_code, 409)
        self.assertTrue(Department.objects.filter(id=dept.id).exists())

    def test_org_structure_for_employee_returns_basic_members(self):
        dept = Department.objects.create(name="Support", is_active=True)
        pos = Position.objects.create(name="Spec", is_active=True)
        self.employee.department = dept
        self.employee.position = pos
        self.employee.telegram = "@hidden"
        self.employee.phone = "+111"
        self.employee.save()

        self.client.force_authenticate(self.employee)
        response = self.client.get("/api/v1/accounts/org/structure/")
        self.assertEqual(response.status_code, 200)
        departments = response.data["departments"]
        support = next(d for d in departments if d["id"] == dept.id)
        member = next(m for m in support["members"] if m["id"] == self.employee.id)
        self.assertIn("full_name", member)
        self.assertNotIn("telegram", member)


class LoginLandingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.intern_role, _ = Role.objects.get_or_create(
            name=Role.Name.INTERN,
            defaults={"level": Role.Level.INTERN},
        )
        self.admin_role, _ = Role.objects.get_or_create(
            name=Role.Name.ADMIN,
            defaults={"level": Role.Level.ADMIN},
        )
        self.intern = User.objects.create_user(
            username="intern_landing",
            password="StrongPass123!",
            role=self.intern_role,
        )
        self.admin = User.objects.create_user(
            username="admin_landing",
            password="StrongPass123!",
            role=self.admin_role,
        )

    def test_intern_login_returns_intern_landing(self):
        response = self.client.post(
            "/api/v1/accounts/login/",
            {"username": "intern_landing", "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["landing"], "intern_portal")
        self.assertTrue(response.data["user"]["is_first_login"])

    def test_admin_login_returns_admin_landing(self):
        response = self.client.post(
            "/api/v1/accounts/login/",
            {"username": "admin_landing", "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["landing"], "admin_panel")
