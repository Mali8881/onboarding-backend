from django.test import TestCase
from unittest.mock import patch
from rest_framework.test import APIClient

from accounts.models import Role, User
from common.models import Notification


class NotificationsApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.role, _ = Role.objects.get_or_create(
            name=Role.Name.EMPLOYEE,
            defaults={"level": Role.Level.EMPLOYEE},
        )
        self.user = User.objects.create_user(
            username="u1",
            password="StrongPass123!",
            role=self.role,
        )
        self.client.force_authenticate(user=self.user)
        self.notification = Notification.objects.create(
            user=self.user,
            title="Title",
            message="Msg",
            type=Notification.Type.INFO,
            is_read=False,
        )

    @patch("common.views.CommonAuditService.log_notification_marked_read")
    def test_mark_single_notification_read(self, log_notification_marked_read):
        response = self.client.patch(
            f"/api/v1/common/notifications/{self.notification.id}/read/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)
        log_notification_marked_read.assert_called_once()

    @patch("common.views.CommonAuditService.log_notifications_marked_read_all")
    def test_mark_all_notifications_read(self, log_notifications_marked_read_all):
        Notification.objects.create(
            user=self.user,
            title="Title2",
            message="Msg2",
            type=Notification.Type.INFO,
            is_read=False,
        )

        response = self.client.patch("/api/v1/common/notifications/read-all/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Notification.objects.filter(user=self.user, is_read=False).exists())
        log_notifications_marked_read_all.assert_called_once()
