from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import AuditLog, Role, User
from work_schedule.models import UserWorkSchedule, WorkSchedule


class WorkScheduleAuditEventsTests(TestCase):
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
        self.employee = User.objects.create_user(
            username="employee_audit_ws",
            password="StrongPass123!",
            role=self.employee_role,
        )
        self.admin = User.objects.create_user(
            username="admin_audit_ws",
            password="StrongPass123!",
            role=self.admin_role,
        )
        self.schedule = WorkSchedule.objects.create(
            name="Office",
            work_days=[0, 1, 2, 3, 4],
            start_time="09:00",
            end_time="18:00",
            is_active=True,
        )

    def test_template_create_update_deactivate_audited(self):
        self.client.force_authenticate(user=self.admin)
        create_response = self.client.post(
            "/api/v1/work-schedules/admin/templates/",
            {
                "name": "Custom",
                "work_days": [0, 1, 2, 3, 4],
                "start_time": "09:00",
                "end_time": "18:00",
                "is_active": True,
                "is_default": False,
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, 201)
        schedule_id = create_response.data["id"]

        update_response = self.client.patch(
            f"/api/v1/work-schedules/admin/templates/{schedule_id}/",
            {"name": "Custom v2"},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)

        deactivate_response = self.client.patch(
            f"/api/v1/work-schedules/admin/templates/{schedule_id}/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(deactivate_response.status_code, 200)

        self.assertTrue(AuditLog.objects.filter(action="work_schedule_created", object_id=str(schedule_id)).exists())
        self.assertTrue(AuditLog.objects.filter(action="work_schedule_updated", object_id=str(schedule_id)).exists())
        self.assertTrue(AuditLog.objects.filter(action="work_schedule_deactivated", object_id=str(schedule_id)).exists())

    def test_request_approve_reject_audited(self):
        self.client.force_authenticate(user=self.employee)
        select_response = self.client.post(
            "/api/v1/work-schedules/select/",
            {"schedule_id": self.schedule.id},
            format="json",
        )
        self.assertEqual(select_response.status_code, 200)
        assignment = UserWorkSchedule.objects.get(user=self.employee)

        self.client.force_authenticate(user=self.admin)
        approve = self.client.post(
            f"/api/v1/work-schedules/admin/requests/{assignment.id}/decision/",
            {"approved": True},
            format="json",
        )
        self.assertEqual(approve.status_code, 200)
        reject = self.client.post(
            f"/api/v1/work-schedules/admin/requests/{assignment.id}/decision/",
            {"approved": False},
            format="json",
        )
        self.assertEqual(reject.status_code, 200)

        self.assertTrue(AuditLog.objects.filter(action="schedule_request_approved", object_id=str(assignment.id)).exists())
        self.assertTrue(AuditLog.objects.filter(action="schedule_request_rejected", object_id=str(assignment.id)).exists())

