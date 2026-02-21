from unittest.mock import patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import Department, Permission, Role, User
from content.models import Course, CourseEnrollment, Feedback
from content.views import FeedbackAdminView, FeedbackCreateView
from onboarding_core.models import OnboardingDay, OnboardingProgress


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


class CoursesFlowTests(TestCase):
    def setUp(self):
        self.intern_role, _ = Role.objects.get_or_create(
            name=Role.Name.INTERN,
            defaults={"level": Role.Level.INTERN},
        )
        self.employee_role, _ = Role.objects.get_or_create(
            name=Role.Name.EMPLOYEE,
            defaults={"level": Role.Level.EMPLOYEE},
        )
        self.admin_role, _ = Role.objects.get_or_create(
            name=Role.Name.ADMIN,
            defaults={"level": Role.Level.ADMIN},
        )

        self.sales = Department.objects.create(name="Sales")
        self.hr = Department.objects.create(name="HR")

        self.admin = User.objects.create_user(
            username="admin_user",
            password="StrongPass123!",
            role=self.admin_role,
            department=self.hr,
        )
        self.employee = User.objects.create_user(
            username="employee_user",
            password="StrongPass123!",
            role=self.employee_role,
            department=self.sales,
        )
        self.intern = User.objects.create_user(
            username="intern_user",
            password="StrongPass123!",
            role=self.intern_role,
            department=self.sales,
        )

        self.public_course = Course.objects.create(
            title="Public Course",
            visibility=Course.Visibility.PUBLIC,
            is_active=True,
        )
        self.sales_course = Course.objects.create(
            title="Sales Course",
            visibility=Course.Visibility.DEPARTMENT,
            department=self.sales,
            is_active=True,
        )
        self.hr_course = Course.objects.create(
            title="HR Course",
            visibility=Course.Visibility.DEPARTMENT,
            department=self.hr,
            is_active=True,
        )

    def test_intern_menu_blocked_until_onboarding_completed(self):
        self.client.force_authenticate(self.intern)
        blocked_response = self.client.get("/api/v1/content/courses/menu-access/")
        self.assertEqual(blocked_response.status_code, status.HTTP_200_OK)
        self.assertFalse(blocked_response.data["has_access"])

        day = OnboardingDay.objects.create(day_number=1, title="Intro", is_active=True)
        OnboardingProgress.objects.create(
            user=self.intern,
            day=day,
            status=OnboardingProgress.Status.DONE,
        )
        allowed_response = self.client.get("/api/v1/content/courses/menu-access/")
        self.assertEqual(allowed_response.status_code, status.HTTP_200_OK)
        self.assertTrue(allowed_response.data["has_access"])

    def test_admin_assign_to_all_excludes_interns(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/v1/content/admin/courses/assign/",
            {
                "course_id": str(self.public_course.id),
                "assign_to_all": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertTrue(
            CourseEnrollment.objects.filter(
                course=self.public_course,
                user=self.employee,
                source=CourseEnrollment.Source.ADMIN,
            ).exists()
        )
        self.assertFalse(
            CourseEnrollment.objects.filter(
                course=self.public_course,
                user=self.intern,
            ).exists()
        )

    def test_employee_can_self_enroll_available_courses_and_update_progress(self):
        self.client.force_authenticate(self.employee)

        available_response = self.client.get("/api/v1/content/courses/available/")
        self.assertEqual(available_response.status_code, status.HTTP_200_OK)
        available_ids = {str(item["id"]) for item in available_response.data}
        self.assertIn(str(self.public_course.id), available_ids)
        self.assertIn(str(self.sales_course.id), available_ids)
        self.assertNotIn(str(self.hr_course.id), available_ids)

        enroll_response = self.client.post(
            "/api/v1/content/courses/self-enroll/",
            {"course_id": str(self.sales_course.id)},
            format="json",
        )
        self.assertEqual(enroll_response.status_code, status.HTTP_201_CREATED)
        enrollment_id = enroll_response.data["id"]

        progress_response = self.client.post(
            "/api/v1/content/courses/progress/",
            {
                "enrollment_id": enrollment_id,
                "progress_percent": 100,
            },
            format="json",
        )
        self.assertEqual(progress_response.status_code, status.HTTP_200_OK)
        self.assertEqual(progress_response.data["status"], CourseEnrollment.Status.COMPLETED)
        self.assertEqual(progress_response.data["progress_percent"], 100)

