from django.test import TestCase
from rest_framework.test import APIClient
from unittest.mock import patch

from accounts.models import Role, User
from work_schedule.models import WorkSchedule, UserWorkSchedule


class ChooseScheduleAuditTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.role, _ = Role.objects.get_or_create(
            name=Role.Name.EMPLOYEE,
            defaults={"level": Role.Level.EMPLOYEE},
        )
        self.user = User.objects.create_user(
            username="ws_user",
            password="StrongPass123!",
            role=self.role,
        )
        self.client.force_authenticate(user=self.user)
        self.schedule = WorkSchedule.objects.create(
            name="Office",
            work_days=[0, 1, 2, 3, 4],
            start_time="09:00",
            end_time="18:00",
            is_active=True,
        )

    @patch("work_schedule.views.WorkScheduleAuditService.log_schedule_selection_invalid_payload")
    def test_choose_schedule_missing_id_logs_invalid_payload(self, log_invalid_payload):
        response = self.client.post("/api/choose-schedule/", {}, format="json")
        self.assertEqual(response.status_code, 400)
        log_invalid_payload.assert_called_once()

    @patch("work_schedule.views.WorkScheduleAuditService.log_schedule_selection_not_found")
    def test_choose_schedule_not_found_logs_event(self, log_not_found):
        response = self.client.post(
            "/api/choose-schedule/",
            {"schedule_id": 999999},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        log_not_found.assert_called_once()

    @patch("work_schedule.views.WorkScheduleAuditService.log_schedule_selected_for_approval")
    def test_choose_schedule_success_logs_selected_event_once(self, log_selected):
        response = self.client.post(
            "/api/choose-schedule/",
            {"schedule_id": self.schedule.id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(UserWorkSchedule.objects.filter(user=self.user).exists())
        log_selected.assert_called_once()

