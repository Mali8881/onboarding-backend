from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Role, User
from work_schedule.models import ProductionCalendar, UserWorkSchedule, WorkSchedule


class WorkScheduleProductionApiTests(TestCase):
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
            username="employee_ws",
            password="StrongPass123!",
            role=self.employee_role,
        )
        self.admin = User.objects.create_user(
            username="admin_ws",
            password="StrongPass123!",
            role=self.admin_role,
        )
        self.super_admin = User.objects.create_user(
            username="super_admin_ws",
            password="StrongPass123!",
            role=self.super_admin_role,
        )
        self.teamlead_like = User.objects.create_user(
            username="lead_ws",
            password="StrongPass123!",
            role=self.employee_role,
        )
        self.subordinate = User.objects.create_user(
            username="sub_ws",
            password="StrongPass123!",
            role=self.employee_role,
            manager=self.teamlead_like,
        )
        self.base_schedule = WorkSchedule.objects.create(
            name="Office 5/2",
            work_days=[0, 1, 2, 3, 4],
            start_time="09:00",
            end_time="18:00",
            is_active=True,
        )

    def test_employee_cannot_create_template(self):
        self.client.force_authenticate(user=self.employee)
        response = self.client.post(
            "/api/v1/work-schedules/admin/templates/",
            {
                "name": "Night",
                "work_days": [0, 1, 2],
                "start_time": "20:00",
                "end_time": "04:00",
                "is_active": True,
                "is_default": False,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_and_update_template(self):
        self.client.force_authenticate(user=self.admin)
        create_response = self.client.post(
            "/api/v1/work-schedules/admin/templates/",
            {
                "name": "Morning",
                "work_days": [0, 1, 2, 3, 4],
                "start_time": "08:00",
                "end_time": "17:00",
                "is_active": True,
                "is_default": False,
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, 201)
        schedule_id = create_response.data["id"]

        patch_response = self.client.patch(
            f"/api/v1/work-schedules/admin/templates/{schedule_id}/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertFalse(patch_response.data["is_active"])

    def test_select_and_approve_flow(self):
        self.client.force_authenticate(user=self.employee)
        select_response = self.client.post(
            "/api/v1/work-schedules/select/",
            {"schedule_id": self.base_schedule.id},
            format="json",
        )
        self.assertEqual(select_response.status_code, 200)
        assignment = UserWorkSchedule.objects.get(user=self.employee)
        self.assertFalse(assignment.approved)

        self.client.force_authenticate(user=self.admin)
        approve_response = self.client.post(
            f"/api/v1/work-schedules/admin/requests/{assignment.id}/decision/",
            {"approved": True},
            format="json",
        )
        self.assertEqual(approve_response.status_code, 200)
        assignment.refresh_from_db()
        self.assertTrue(assignment.approved)
        self.client.force_authenticate(user=self.employee)
        my_response = self.client.get("/api/v1/work-schedules/my/")
        self.assertEqual(my_response.status_code, 200)
        self.assertEqual(my_response.data["status"], "approved")

    def test_admin_can_view_users_for_template(self):
        UserWorkSchedule.objects.create(
            user=self.employee,
            schedule=self.base_schedule,
            approved=False,
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(f"/api/v1/work-schedules/admin/templates/{self.base_schedule.id}/users/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_employee_cannot_access_admin_requests(self):
        self.client.force_authenticate(user=self.employee)
        response = self.client.get("/api/v1/work-schedules/admin/requests/")
        self.assertEqual(response.status_code, 403)

    def test_teamlead_like_employee_cannot_access_admin_requests(self):
        self.client.force_authenticate(user=self.teamlead_like)
        response = self.client.get("/api/v1/work-schedules/admin/requests/")
        self.assertEqual(response.status_code, 403)

    def test_super_admin_can_access_admin_requests(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.get("/api/v1/work-schedules/admin/requests/")
        self.assertEqual(response.status_code, 200)

    def test_calendar_generate_is_idempotent(self):
        self.client.force_authenticate(user=self.admin)
        first = self.client.post(
            "/api/v1/work-schedules/admin/calendar/generate/",
            {"year": 2026, "month": 3, "overwrite": False},
            format="json",
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data["created"], 31)
        self.assertEqual(first.data["updated"], 0)

        second = self.client.post(
            "/api/v1/work-schedules/admin/calendar/generate/",
            {"year": 2026, "month": 3, "overwrite": False},
            format="json",
        )
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data["created"], 0)
        self.assertEqual(second.data["updated"], 0)

        third = self.client.post(
            "/api/v1/work-schedules/admin/calendar/generate/",
            {"year": 2026, "month": 3, "overwrite": True},
            format="json",
        )
        self.assertEqual(third.status_code, 200)
        self.assertEqual(ProductionCalendar.objects.filter(date__year=2026, date__month=3).count(), 31)
