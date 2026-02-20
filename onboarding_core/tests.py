from django.test import TestCase
from rest_framework.test import APIClient
from unittest.mock import patch

from accounts.models import Permission, Role, User
from onboarding_core.models import OnboardingDay, OnboardingProgress


class OnboardingFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.role, _ = Role.objects.get_or_create(
            name=Role.Name.INTERN,
            defaults={"level": Role.Level.INTERN},
        )
        self.user = User.objects.create_user(
            username="intern",
            password="StrongPass123!",
            role=self.role,
        )
        self.day1 = OnboardingDay.objects.create(day_number=1, title="Day 1", is_active=True)
        self.day2 = OnboardingDay.objects.create(day_number=2, title="Day 2", is_active=True)
        self.client.force_authenticate(user=self.user)

    def test_can_complete_second_day_without_first_day(self):
        response = self.client.post(f"/api/v1/onboarding/days/{self.day2.id}/complete/")
        self.assertEqual(response.status_code, 200)

        progress = OnboardingProgress.objects.get(user=self.user, day=self.day2)
        self.assertEqual(progress.status, OnboardingProgress.Status.DONE)

    def test_complete_day_is_idempotent(self):
        first = self.client.post(f"/api/v1/onboarding/days/{self.day1.id}/complete/")
        second = self.client.post(f"/api/v1/onboarding/days/{self.day1.id}/complete/")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data["status"], OnboardingProgress.Status.DONE)

    def test_overview_no_locked_statuses(self):
        response = self.client.get("/api/v1/onboarding/overview/")
        self.assertEqual(response.status_code, 200)

        statuses = {item["status"] for item in response.data["days"]}
        self.assertNotIn("LOCKED", statuses)

    @patch("onboarding_core.views.OnboardingAuditService.log_day_completed")
    def test_complete_logs_audit_payload(self, log_day_completed):
        response = self.client.post(f"/api/v1/onboarding/days/{self.day1.id}/complete/")
        self.assertEqual(response.status_code, 200)

        log_day_completed.assert_called_once()
        _, kwargs = log_day_completed.call_args
        self.assertFalse(kwargs["idempotent"])

    @patch("onboarding_core.views.OnboardingAuditService.log_day_completed")
    def test_idempotent_complete_logs_once_with_idempotent_flag(self, log_day_completed):
        self.client.post(f"/api/v1/onboarding/days/{self.day1.id}/complete/")
        log_day_completed.reset_mock()

        response = self.client.post(f"/api/v1/onboarding/days/{self.day1.id}/complete/")
        self.assertEqual(response.status_code, 200)

        log_day_completed.assert_called_once()
        _, kwargs = log_day_completed.call_args
        self.assertTrue(kwargs["idempotent"])

    @patch("onboarding_core.views.OnboardingAuditService.log_overview_viewed")
    def test_overview_logs_audit_once(self, log_overview_viewed):
        response = self.client.get("/api/v1/onboarding/overview/")
        self.assertEqual(response.status_code, 200)

        log_overview_viewed.assert_called_once()
        _, kwargs = log_overview_viewed.call_args
        self.assertEqual(kwargs["total_days"], 2)
        self.assertEqual(kwargs["completed_days"], 0)


class OnboardingAdminAuditTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.permission, _ = Permission.objects.get_or_create(
            codename="reports_review",
            defaults={"module": "onboarding"},
        )
        self.role, _ = Role.objects.get_or_create(
            name=Role.Name.ADMIN,
            defaults={"level": Role.Level.ADMIN},
        )
        self.role.permissions.add(self.permission)

        self.user = User.objects.create_user(
            username="admin_u",
            password="StrongPass123!",
            role=self.role,
        )
        self.client.force_authenticate(user=self.user)

        self.day = OnboardingDay.objects.create(day_number=10, title="Day 10", is_active=True)
        OnboardingProgress.objects.create(user=self.user, day=self.day, status=OnboardingProgress.Status.IN_PROGRESS)

    @patch("onboarding_core.views.OnboardingAuditService.log_progress_viewed_admin")
    def test_admin_progress_list_logs_audit_once(self, log_progress_viewed_admin):
        response = self.client.get("/api/v1/onboarding/admin/onboarding/progress/?status=in_progress")
        self.assertEqual(response.status_code, 200)

        log_progress_viewed_admin.assert_called_once()
        args, _ = log_progress_viewed_admin.call_args
        self.assertEqual(args[1]["status"], "in_progress")
