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
            {
                "name": "Backend",
                "parent": parent.id,
                "comment": "Подраздел backend-платформы",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["parent"], parent.id)
        self.assertEqual(response.data["comment"], "Подраздел backend-платформы")

    def test_employee_cannot_create_department(self):
        self.client.force_authenticate(self.employee)
        response = self.client.post(
            "/api/v1/accounts/org/departments/",
            {"name": "Forbidden"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_can_update_department_comment_via_compat_endpoint(self):
        self.client.force_authenticate(self.admin)
        parent = Department.objects.create(name="Finance")
        item = Department.objects.create(name="Payroll", parent=parent)
        response = self.client.patch(
            f"/api/v1/auth/departments/{item.id}/",
            {"comment": "Ответственный за начисления и сверку", "parent": parent.id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.comment, "Ответственный за начисления и сверку")
        self.assertEqual(item.parent_id, parent.id)

    def test_employee_cannot_update_department_via_compat_endpoint(self):
        self.client.force_authenticate(self.employee)
        item = Department.objects.create(name="Support")
        response = self.client.patch(
            f"/api/v1/auth/departments/{item.id}/",
            {"comment": "forbidden"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_subdivision_via_alias_endpoint(self):
        self.client.force_authenticate(self.admin)
        parent = Department.objects.create(name="Operations")
        response = self.client.post(
            "/api/v1/auth/subdivisions/",
            {"name": "Operations QA", "parent": parent.id, "comment": "Контроль качества"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["parent"], parent.id)
        self.assertEqual(response.data["comment"], "Контроль качества")

    def test_subdivision_requires_parent(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/v1/accounts/org/subdivisions/",
            {"name": "No parent subdivision"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("parent", response.data)

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


class TeamleadManagerCleanupTests(TestCase):
    def test_demoting_teamlead_clears_manager_for_team_members(self):
        teamlead_role, _ = Role.objects.get_or_create(
            name=Role.Name.TEAMLEAD,
            defaults={"level": Role.Level.TEAMLEAD},
        )
        employee_role, _ = Role.objects.get_or_create(
            name=Role.Name.EMPLOYEE,
            defaults={"level": Role.Level.EMPLOYEE},
        )

        teamlead = User.objects.create_user(
            username="teamlead_cleanup",
            password="StrongPass123!",
            role=teamlead_role,
        )
        employee = User.objects.create_user(
            username="employee_cleanup",
            password="StrongPass123!",
            role=employee_role,
            manager=teamlead,
        )

        self.assertEqual(employee.manager_id, teamlead.id)

        teamlead.role = employee_role
        teamlead.save(update_fields=["role"])

        employee.refresh_from_db()
        self.assertIsNone(employee.manager_id)


class TeamleadOrgUsersAccessTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.teamlead_role, _ = Role.objects.get_or_create(
            name=Role.Name.TEAMLEAD,
            defaults={"level": Role.Level.TEAMLEAD},
        )
        self.employee_role, _ = Role.objects.get_or_create(
            name=Role.Name.EMPLOYEE,
            defaults={"level": Role.Level.EMPLOYEE},
        )

        self.teamlead = User.objects.create_user(
            username="teamlead_users_list",
            password="StrongPass123!",
            role=self.teamlead_role,
        )
        self.subordinate = User.objects.create_user(
            username="team_member_1",
            password="StrongPass123!",
            role=self.employee_role,
            manager=self.teamlead,
        )
        self.other_user = User.objects.create_user(
            username="outside_member",
            password="StrongPass123!",
            role=self.employee_role,
        )

    def test_teamlead_sees_only_direct_subordinates_in_org_users(self):
        self.client.force_authenticate(self.teamlead)
        response = self.client.get("/api/v1/accounts/org/users/")
        self.assertEqual(response.status_code, 200)
        usernames = {item["username"] for item in response.data}
        self.assertIn(self.subordinate.username, usernames)
        self.assertNotIn(self.other_user.username, usernames)
        self.assertNotIn(self.teamlead.username, usernames)

    def test_teamlead_can_access_me_team_endpoint(self):
        self.client.force_authenticate(self.teamlead)
        response = self.client.get("/api/v1/accounts/me/team/")
        self.assertEqual(response.status_code, 200)
        ids = {item["id"] for item in response.data}
        self.assertIn(self.subordinate.id, ids)
        self.assertNotIn(self.other_user.id, ids)
