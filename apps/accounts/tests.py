from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    Department,
    DepartmentSubdivision,
    PasswordResetToken,
    Permission,
    Position,
    PromotionRequest,
    Role,
    User,
)


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


class LogoutApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.role, _ = Role.objects.get_or_create(
            name=Role.Name.EMPLOYEE,
            defaults={"level": Role.Level.EMPLOYEE},
        )
        self.user = User.objects.create_user(
            username="logout_user",
            password="StrongPass123!",
            role=self.role,
        )

    def test_logout_endpoint_exists_and_returns_ok(self):
        self.client.force_authenticate(user=self.user)
        refresh = str(RefreshToken.for_user(self.user))
        response = self.client.post("/api/v1/accounts/logout/", {"refresh": refresh}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get("detail"), "Logged out.")

    def test_legacy_my_password_route_is_available(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/accounts/me/password/",
            {
                "current_password": "StrongPass123!",
                "new_password": "NewStrongPass123!",
                "new_password_confirm": "NewStrongPass123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)


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


class DepartmentTransferUsersApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.role_admin, _ = Role.objects.get_or_create(
            name=Role.Name.ADMIN,
            defaults={"level": Role.Level.ADMIN},
        )
        self.role_employee, _ = Role.objects.get_or_create(
            name=Role.Name.EMPLOYEE,
            defaults={"level": Role.Level.EMPLOYEE},
        )
        self.admin = User.objects.create_user(
            username="transfer_admin",
            password="StrongPass123!",
            role=self.role_admin,
        )
        self.employee = User.objects.create_user(
            username="transfer_employee",
            password="StrongPass123!",
            role=self.role_employee,
        )

    def test_admin_can_transfer_users_between_departments(self):
        self.client.force_authenticate(self.admin)
        source = Department.objects.create(name="Source", is_active=True)
        target = Department.objects.create(name="Target", is_active=True)
        self.employee.department = source
        self.employee.save(update_fields=["department"])

        response = self.client.post(
            f"/api/v1/accounts/org/departments/{source.id}/transfer-users/",
            {"target_department_id": target.id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get("moved_count"), 1)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.department_id, target.id)


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


class PromotionApprovalMappingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.role_admin, _ = Role.objects.get_or_create(
            name=Role.Name.ADMIN,
            defaults={"level": Role.Level.ADMIN},
        )
        self.role_intern, _ = Role.objects.get_or_create(
            name=Role.Name.INTERN,
            defaults={"level": Role.Level.INTERN},
        )
        self.role_employee, _ = Role.objects.get_or_create(
            name=Role.Name.EMPLOYEE,
            defaults={"level": Role.Level.EMPLOYEE},
        )

        self.department_it = Department.objects.create(name="IT Department", is_active=True)
        self.department_sales = Department.objects.create(name="Sales Department", is_active=True)
        self.subdivision_backend = DepartmentSubdivision.objects.create(
            department=self.department_it,
            name="Backend",
            is_active=True,
        )

        self.admin = User.objects.create_user(
            username="promo_admin",
            password="StrongPass123!",
            role=self.role_admin,
        )
        self.intern = User.objects.create_user(
            username="promo_intern",
            password="StrongPass123!",
            role=self.role_intern,
            department=self.department_sales,
            subdivision=self.subdivision_backend,
        )

    def test_approve_promotion_maps_department_from_selected_subdivision(self):
        request_item = PromotionRequest.objects.create(
            user=self.intern,
            requested_role=self.role_employee,
            reason="Move to employee",
        )
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            f"/api/auth/promotion-requests/{request_item.id}/approve/",
            {"comment": "Approved"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        self.intern.refresh_from_db()
        self.assertEqual(self.intern.role_id, self.role_employee.id)
        self.assertEqual(self.intern.subdivision_id, self.subdivision_backend.id)
        self.assertEqual(self.intern.department_id, self.department_it.id)


class RolesApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.role_superadmin, _ = Role.objects.get_or_create(
            name=Role.Name.SUPER_ADMIN,
            defaults={"level": Role.Level.SUPER_ADMIN},
        )
        self.role_admin, _ = Role.objects.get_or_create(
            name=Role.Name.ADMIN,
            defaults={"level": Role.Level.ADMIN},
        )
        self.role_employee, _ = Role.objects.get_or_create(
            name=Role.Name.EMPLOYEE,
            defaults={"level": Role.Level.EMPLOYEE},
        )
        self.role_permission, _ = Role.objects.get_or_create(
            name="CUSTOM_TEST_ROLE",
            defaults={"level": 35, "description": "Role for tests"},
        )

        self.perm_roles_manage, _ = Permission.objects.get_or_create(
            codename="roles_manage",
            defaults={
                "module": "accounts",
                "description": "Manage roles",
            },
        )
        self.role_superadmin.permissions.add(self.perm_roles_manage)

        self.superadmin = User.objects.create_user(
            username="roles_superadmin",
            password="StrongPass123!",
            role=self.role_superadmin,
        )
        self.admin = User.objects.create_user(
            username="roles_admin",
            password="StrongPass123!",
            role=self.role_admin,
        )

    def test_admin_can_list_roles(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/v1/accounts/org/roles/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(isinstance(response.data, list))

    def test_admin_cannot_create_role_without_permission(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/v1/accounts/org/roles/",
            {"name": "NEW_ROLE_NO_PERMISSION", "level": 25},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_superadmin_with_roles_manage_can_create_role(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.post(
            "/api/v1/accounts/org/roles/",
            {"name": "NEW_ROLE_ALLOWED", "level": 25, "description": "created from test"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "NEW_ROLE_ALLOWED")
