from unittest.mock import patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import Permission, Role, User
from content.models import Feedback
from content.views import FeedbackAdminView, FeedbackCreateView


class FeedbackAuditTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.permission, _ = Permission.objects.get_or_create(
            codename="feedback_manage",
            defaults={"module": "content"},
        )
        self.role, _ = Role.objects.get_or_create(
            name=Role.Name.ADMIN,
            defaults={"level": Role.Level.ADMIN},
        )
        self.role.permissions.add(self.permission)

        self.admin = User.objects.create_user(
            username="content_admin",
            password="StrongPass123!",
            role=self.role,
        )

    @patch("content.views.ContentAuditService.log_feedback_created")
    def test_feedback_create_logs_event_once(self, log_feedback_created):
        request = self.factory.post(
            "/api/v1/content/feedback/",
            {
                "type": "complaint",
                "text": "Feedback text",
                "full_name": "",
                "contact": "",
            },
            format="json",
        )
        response = FeedbackCreateView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        log_feedback_created.assert_called_once()

    @patch("content.views.ContentAuditService.log_feedback_status_changed_admin")
    @patch("content.views.ContentAuditService.log_feedback_updated_admin")
    def test_feedback_admin_update_logs_update_event(self, log_feedback_updated_admin, log_feedback_status_changed_admin):
        feedback = Feedback.objects.create(
            type="complaint",
            text="Old text",
            is_anonymous=True,
        )

        request = self.factory.patch(
            f"/api/v1/content/admin/feedback/{feedback.id}/",
            {"text": "New text"},
            format="json",
        )
        force_authenticate(request, user=self.admin)

        view = FeedbackAdminView.as_view({"patch": "partial_update"})
        response = view(request, pk=str(feedback.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        log_feedback_updated_admin.assert_called_once()
        log_feedback_status_changed_admin.assert_not_called()

