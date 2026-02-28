from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase, force_authenticate

from accounts.models import Department, Permission, Role, User
from content.models import Course, CourseEnrollment, Feedback
from content.views import FeedbackCreateView
from onboarding_core.models import OnboardingDay, OnboardingProgress


class FeedbackAccessTests(APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.permission, _ = Permission.objects.get_or_create(
            codename="feedback_manage",
            defaults={"module": "content"},
        )
        self.super_role, _ = Role.objects.get_or_create(
            name=Role.Name.SUPER_ADMIN,
            defaults={"level": Role.Level.SUPER_ADMIN},
        )
        self.admin_role, _ = Role.objects.get_or_create(
            name=Role.Name.ADMIN,
            defaults={"level": Role.Level.ADMIN},
        )
        self.admin_no_perm_role, _ = Role.objects.get_or_create(
            name="ADMIN_NO_FEEDBACK",
            defaults={"level": Role.Level.ADMIN},
        )
        self.employee_role, _ = Role.objects.get_or_create(
            name=Role.Name.EMPLOYEE,
            defaults={"level": Role.Level.EMPLOYEE},
        )
        self.intern_role, _ = Role.objects.get_or_create(
            name=Role.Name.INTERN,
            defaults={"level": Role.Level.INTERN},
        )
        self.super_role.permissions.add(self.permission)
        self.admin_role.permissions.add(self.permission)

        self.superadmin = User.objects.create_user(
            username="content_super",
            password="StrongPass123!",
            role=self.super_role,
            email="super@example.com",
            first_name="Super",
            last_name="Admin",
        )
        self.admin = User.objects.create_user(
            username="content_admin",
            password="StrongPass123!",
            role=self.admin_role,
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
        )
        self.admin_no_perm = User.objects.create_user(
            username="content_admin_no_perm",
            password="StrongPass123!",
            role=self.admin_no_perm_role,
        )
        self.employee = User.objects.create_user(
            username="content_employee",
            password="StrongPass123!",
            role=self.employee_role,
            email="employee@example.com",
            first_name="Emp",
            last_name="Loyee",
        )
        self.intern = User.objects.create_user(
            username="content_intern",
            password="StrongPass123!",
            role=self.intern_role,
            email="intern@example.com",
            first_name="In",
            last_name="Tern",
        )

    def _feedback_payload(self, is_anonymous=True):
        return {
            "type": "review",
            "text": "Feedback text",
            "is_anonymous": is_anonymous,
        }

    @patch("content.views.ContentAuditService.log_feedback_created")
    def test_all_roles_use_same_feedback_payload_and_can_be_anonymous(self, log_feedback_created):
        users = [self.superadmin, self.admin, self.employee, self.intern]
        for user in users:
            self.client.force_authenticate(user=user)
            response = self.client.post("/api/v1/content/feedback/", self._feedback_payload(True), format="json")
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

            created = Feedback.objects.filter(sender=user).latest("created_at")
            self.assertEqual(created.recipient, "SUPER_ADMIN")
            self.assertTrue(created.is_anonymous)
            self.assertIsNone(created.full_name)
            self.assertIsNone(created.contact)
        self.assertEqual(log_feedback_created.call_count, 4)

    def test_non_anonymous_feedback_autofills_author(self):
        self.client.force_authenticate(user=self.employee)
        response = self.client.post("/api/v1/content/feedback/", self._feedback_payload(False), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Feedback.objects.get(sender=self.employee)
        self.assertEqual(created.recipient, "SUPER_ADMIN")
        self.assertEqual(created.full_name, "Emp Loyee")
        self.assertEqual(created.contact, "employee@example.com")
        self.assertFalse(created.is_anonymous)

    def test_feedback_admin_requires_feedback_manage_and_admin_like(self):
        self.client.force_authenticate(user=self.admin_no_perm)
        denied_no_permission = self.client.get("/api/v1/content/admin/feedback/")
        self.assertEqual(denied_no_permission.status_code, status.HTTP_403_FORBIDDEN)

        self.employee_role.permissions.add(self.permission)
        self.client.force_authenticate(user=self.employee)
        denied_not_admin_like = self.client.get("/api/v1/content/admin/feedback/")
        self.assertEqual(denied_not_admin_like.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.admin)
        allowed_admin = self.client.get("/api/v1/content/admin/feedback/")
        self.assertEqual(allowed_admin.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=self.superadmin)
        allowed_superadmin = self.client.get("/api/v1/content/admin/feedback/")
        self.assertEqual(allowed_superadmin.status_code, status.HTTP_200_OK)

    def test_only_superadmin_can_mark_read_or_accept(self):
        feedback = Feedback.objects.create(
            type="complaint",
            text="Old text",
            is_anonymous=True,
            sender=self.employee,
            recipient="SUPER_ADMIN",
        )

        self.client.force_authenticate(user=self.admin)
        denied = self.client.post(
            f"/api/v1/content/admin/feedback/{feedback.id}/set-status/",
            {"status": "accepted"},
            format="json",
        )
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.superadmin)
        allowed = self.client.post(
            f"/api/v1/content/admin/feedback/{feedback.id}/set-status/",
            {"status": "accepted"},
            format="json",
        )
        self.assertEqual(allowed.status_code, status.HTTP_200_OK)
        feedback.refresh_from_db()
        self.assertEqual(feedback.status, "accepted")
        self.assertTrue(feedback.is_read)

    @patch("content.views.ContentAuditService.log_feedback_status_changed_admin")
    @patch("content.views.ContentAuditService.log_feedback_updated_admin")
    def test_superadmin_update_logs_events(self, log_feedback_updated_admin, log_feedback_status_changed_admin):
        feedback = Feedback.objects.create(
            type="complaint",
            text="Old text",
            is_anonymous=True,
            sender=self.employee,
            recipient="SUPER_ADMIN",
        )

        self.client.force_authenticate(user=self.admin)
        denied = self.client.patch(
            f"/api/v1/content/admin/feedback/{feedback.id}/",
            {"status": "in_progress"},
            format="json",
        )
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)
        log_feedback_updated_admin.assert_not_called()
        log_feedback_status_changed_admin.assert_not_called()

        self.client.force_authenticate(user=self.superadmin)
        allowed = self.client.patch(
            f"/api/v1/content/admin/feedback/{feedback.id}/",
            {"status": "in_progress"},
            format="json",
        )
        self.assertEqual(allowed.status_code, status.HTTP_200_OK)
        log_feedback_updated_admin.assert_called_once()
        log_feedback_status_changed_admin.assert_called_once()

    def test_feedback_admin_stats_and_screen_fields(self):
        Feedback.objects.create(type="review", text="f1", status="new", is_read=False, sender=self.employee, recipient="SUPER_ADMIN")
        Feedback.objects.create(type="review", text="f2", status="in_progress", is_read=True, sender=self.employee, recipient="SUPER_ADMIN")
        Feedback.objects.create(type="review", text="f3", status="accepted", is_read=True, sender=self.employee, recipient="SUPER_ADMIN")
        Feedback.objects.create(type="review", text="f4", status="closed", is_read=True, sender=self.employee, recipient="SUPER_ADMIN")

        self.client.force_authenticate(user=self.superadmin)
        stats_response = self.client.get("/api/v1/content/admin/feedback/stats/")
        self.assertEqual(stats_response.status_code, status.HTTP_200_OK)
        self.assertEqual(stats_response.data["total"], 4)
        self.assertEqual(stats_response.data["new"], 1)
        self.assertEqual(stats_response.data["in_progress"], 1)
        self.assertEqual(stats_response.data["accepted"], 2)
        self.assertEqual(stats_response.data["closed"], 2)

        list_response = self.client.get("/api/v1/content/admin/feedback/")
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(list_response.data) >= 1)
        row = list_response.data[0]
        for key in ("message", "employee_name", "date", "can_mark_read", "can_accept"):
            self.assertIn(key, row)

        self.client.force_authenticate(user=self.admin)
        admin_list_response = self.client.get("/api/v1/content/admin/feedback/")
        self.assertEqual(admin_list_response.status_code, status.HTTP_200_OK)
        if admin_list_response.data:
            self.assertFalse(admin_list_response.data[0]["can_mark_read"])
            self.assertFalse(admin_list_response.data[0]["can_accept"])

    @patch("content.views.ContentAuditService.log_feedback_created")
    def test_feedback_create_logs_event_once(self, log_feedback_created):
        request = self.factory.post(
            "/api/v1/content/feedback/",
            {
                "type": "complaint",
                "text": "Feedback text",
                "is_anonymous": True,
            },
            format="json",
        )
        force_authenticate(request, user=self.admin)
        response = FeedbackCreateView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        log_feedback_created.assert_called_once()


class CoursesFlowTests(APITestCase):
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

