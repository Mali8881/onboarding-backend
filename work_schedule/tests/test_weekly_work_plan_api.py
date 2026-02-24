from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Role, User
from work_schedule.models import WeeklyWorkPlan


class WeeklyWorkPlanApiTests(TestCase):
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
            username="weekly_employee",
            password="StrongPass123!",
            role=self.employee_role,
        )
        self.admin = User.objects.create_user(
            username="weekly_admin",
            password="StrongPass123!",
            role=self.admin_role,
        )
        self.week_start = date(2026, 3, 2)  # Monday

    def _shifts_payload(self):
        return [
            {"date": "2026-03-02", "start_time": "09:00", "end_time": "13:00", "mode": "office", "comment": ""},
            {"date": "2026-03-03", "start_time": "09:00", "end_time": "13:00", "mode": "office", "comment": ""},
            {"date": "2026-03-04", "start_time": "09:00", "end_time": "13:00", "mode": "office", "comment": ""},
            {"date": "2026-03-05", "start_time": "09:00", "end_time": "13:00", "mode": "office", "comment": ""},
            {"date": "2026-03-06", "start_time": "09:00", "end_time": "13:00", "mode": "office", "comment": ""},
            {"date": "2026-03-07", "start_time": "11:00", "end_time": "13:00", "mode": "office", "comment": ""},
            {"date": "2026-03-08", "start_time": "11:00", "end_time": "13:00", "mode": "office", "comment": ""},
        ]

    def test_employee_can_submit_weekly_plan_with_required_minimums(self):
        self.client.force_authenticate(self.employee)
        response = self.client.post(
            "/api/v1/work-schedules/weekly-plans/my/",
            {
                "week_start": str(self.week_start),
                "days": self._shifts_payload(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        plan = WeeklyWorkPlan.objects.get(user=self.employee, week_start=self.week_start)
        self.assertEqual(plan.status, WeeklyWorkPlan.Status.PENDING)
        self.assertEqual(plan.office_hours, 24)
        self.assertEqual(plan.online_hours, 0)

    def test_online_above_16_requires_reason(self):
        self.client.force_authenticate(self.employee)
        response = self.client.post(
            "/api/v1/work-schedules/weekly-plans/my/",
            {
                "week_start": str(self.week_start),
                "days": [
                    {"date": "2026-03-02", "start_time": "09:00", "end_time": "13:00", "mode": "online"},
                    {"date": "2026-03-03", "start_time": "09:00", "end_time": "13:00", "mode": "online"},
                    {"date": "2026-03-04", "start_time": "09:00", "end_time": "13:00", "mode": "online"},
                    {"date": "2026-03-05", "start_time": "09:00", "end_time": "13:00", "mode": "online"},
                    {"date": "2026-03-06", "start_time": "09:00", "end_time": "13:00", "mode": "online"},
                    {"date": "2026-03-07", "start_time": "11:00", "end_time": "13:00", "mode": "office"},
                    {"date": "2026-03-08", "start_time": "11:00", "end_time": "13:00", "mode": "office"},
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("online_reason", response.data)

    def test_office_hours_below_24_requires_reason(self):
        self.client.force_authenticate(self.employee)
        response = self.client.post(
            "/api/v1/work-schedules/weekly-plans/my/",
            {
                "week_start": str(self.week_start),
                "days": [
                    {"date": "2026-03-02", "start_time": "09:00", "end_time": "11:00", "mode": "office"},
                    {"date": "2026-03-03", "start_time": "09:00", "end_time": "11:00", "mode": "office"},
                    {"date": "2026-03-04", "start_time": "09:00", "end_time": "11:00", "mode": "office"},
                    {"date": "2026-03-05", "start_time": "09:00", "end_time": "11:00", "mode": "office"},
                    {"date": "2026-03-06", "start_time": "09:00", "end_time": "11:00", "mode": "office"},
                    {"date": "2026-03-07", "start_time": "11:00", "end_time": "12:00", "mode": "office"},
                    {"date": "2026-03-08", "start_time": "11:00", "end_time": "12:00", "mode": "office"},
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("online_reason", response.data)

    def test_admin_can_request_clarification_then_approve(self):
        plan = WeeklyWorkPlan.objects.create(
            user=self.employee,
            week_start=self.week_start,
            days=self._shifts_payload(),
            office_hours=24,
            online_hours=0,
            online_reason="Need remote because of medical appointments.",
        )
        self.client.force_authenticate(self.admin)

        clarification = self.client.post(
            f"/api/v1/work-schedules/admin/weekly-plans/{plan.id}/decision/",
            {"action": "request_clarification", "admin_comment": "Please provide specific days."},
            format="json",
        )
        self.assertEqual(clarification.status_code, 200)
        plan.refresh_from_db()
        self.assertEqual(plan.status, WeeklyWorkPlan.Status.CLARIFICATION_REQUESTED)

        approved = self.client.post(
            f"/api/v1/work-schedules/admin/weekly-plans/{plan.id}/decision/",
            {"action": "approve", "admin_comment": "Approved after clarification."},
            format="json",
        )
        self.assertEqual(approved.status_code, 200)
        plan.refresh_from_db()
        self.assertEqual(plan.status, WeeklyWorkPlan.Status.APPROVED)

    def test_employee_cannot_access_admin_weekly_plans(self):
        self.client.force_authenticate(self.employee)
        response = self.client.get("/api/v1/work-schedules/admin/weekly-plans/")
        self.assertEqual(response.status_code, 403)

    def test_weekend_time_limits_are_enforced(self):
        self.client.force_authenticate(self.employee)
        response = self.client.post(
            "/api/v1/work-schedules/weekly-plans/my/",
            {
                "week_start": str(self.week_start),
                "days": [
                    {"date": "2026-03-02", "start_time": "09:00", "end_time": "13:00", "mode": "office"},
                    {"date": "2026-03-03", "start_time": "09:00", "end_time": "13:00", "mode": "office"},
                    {"date": "2026-03-04", "start_time": "09:00", "end_time": "13:00", "mode": "office"},
                    {"date": "2026-03-05", "start_time": "09:00", "end_time": "13:00", "mode": "office"},
                    {"date": "2026-03-06", "start_time": "09:00", "end_time": "13:00", "mode": "office"},
                    {"date": "2026-03-07", "start_time": "09:00", "end_time": "13:00", "mode": "office"},
                    {"date": "2026-03-08", "start_time": "11:00", "end_time": "13:00", "mode": "office"},
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("days", response.data)

    def test_day_off_mode_without_hours_is_allowed(self):
        self.client.force_authenticate(self.employee)
        response = self.client.post(
            "/api/v1/work-schedules/weekly-plans/my/",
            {
                "week_start": str(self.week_start),
                "days": [
                    {"date": "2026-03-02", "start_time": "09:00", "end_time": "15:00", "mode": "office"},
                    {"date": "2026-03-03", "start_time": "09:00", "end_time": "15:00", "mode": "office"},
                    {"date": "2026-03-04", "start_time": "09:00", "end_time": "15:00", "mode": "office"},
                    {"date": "2026-03-05", "start_time": "09:00", "end_time": "15:00", "mode": "office"},
                    {"date": "2026-03-06", "start_time": "09:00", "end_time": "15:00", "mode": "office"},
                    {"date": "2026-03-07", "mode": "day_off"},
                    {"date": "2026-03-08", "mode": "day_off"},
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_resubmit_resets_status_to_pending(self):
        plan = WeeklyWorkPlan.objects.create(
            user=self.employee,
            week_start=self.week_start,
            days=self._shifts_payload(),
            office_hours=24,
            online_hours=0,
            online_reason="Need remote because of medical appointments.",
            status=WeeklyWorkPlan.Status.CLARIFICATION_REQUESTED,
            admin_comment="Clarify exact days.",
            reviewed_by=self.admin,
        )
        self.client.force_authenticate(self.employee)
        response = self.client.post(
            "/api/v1/work-schedules/weekly-plans/my/",
            {
                "week_start": str(self.week_start),
                "days": self._shifts_payload(),
                "employee_comment": "Updated with office focus.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        plan.refresh_from_db()
        self.assertEqual(plan.status, WeeklyWorkPlan.Status.PENDING)
        self.assertEqual(plan.admin_comment, "")
        self.assertIsNone(plan.reviewed_by)
