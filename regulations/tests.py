from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import Department, Role, User
from regulations.models import (
    InternOnboardingRequest,
    Regulation,
    RegulationAcknowledgement,
    RegulationReadReport,
    RegulationQuiz,
    RegulationQuizOption,
    RegulationQuizQuestion,
    RegulationReadProgress,
)


class RegulationsApiTests(APITestCase):
    def setUp(self):
        self.role_admin = Role.objects.create(name=Role.Name.ADMIN, level=Role.Level.ADMIN)
        self.role_employee = Role.objects.create(
            name=Role.Name.EMPLOYEE, level=Role.Level.EMPLOYEE
        )

        user_model = get_user_model()
        self.admin = user_model.objects.create_user(
            username="reg_admin",
            password="StrongPass123!",
            role=self.role_admin,
        )
        self.employee = user_model.objects.create_user(
            username="reg_emp",
            password="StrongPass123!",
            role=self.role_employee,
        )

        self.active_ru = Regulation.objects.create(
            title="RU Active",
            type=Regulation.RegulationType.LINK,
            external_url="https://example.com/ru",
            is_active=True,
            language=Regulation.Language.RU,
            position=1,
        )
        Regulation.objects.create(
            title="RU Inactive",
            type=Regulation.RegulationType.LINK,
            external_url="https://example.com/ru2",
            is_active=False,
            language=Regulation.Language.RU,
            position=2,
        )

    def test_employee_sees_only_active_by_language(self):
        self.client.force_authenticate(self.employee)
        url = reverse("regulations-list")
        response = self.client.get(url, {"language": "ru"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], str(self.active_ru.id))

    def test_employee_cannot_create_admin_regulation(self):
        self.client.force_authenticate(self.employee)
        url = reverse("regulations-admin-list-create")
        response = self.client.post(
            url,
            {
                "title": "Denied",
                "type": "link",
                "external_url": "https://example.com",
                "language": "ru",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_create_requires_link_or_file_by_type(self):
        self.client.force_authenticate(self.admin)
        url = reverse("regulations-admin-list-create")

        bad_response = self.client.post(
            url,
            {
                "title": "Bad Link",
                "type": "link",
                "language": "ru",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(bad_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("external_url", bad_response.data)

        ok_response = self.client.post(
            url,
            {
                "title": "Good Link",
                "type": "link",
                "external_url": "https://example.com/reg",
                "language": "ru",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(ok_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ok_response.data["type"], "link")

    def test_public_list_supports_filters_and_action_field(self):
        self.client.force_authenticate(self.employee)
        Regulation.objects.create(
            title="HR File",
            type=Regulation.RegulationType.FILE,
            file=SimpleUploadedFile("doc.pdf", b"dummy", content_type="application/pdf"),
            is_active=True,
            language=Regulation.Language.RU,
            position=3,
        )
        url = reverse("regulations-list")
        response = self.client.get(url, {"language": "ru", "type": "file", "q": "HR"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["action"], "open")

    def test_public_list_includes_overdue_state_for_unread(self):
        overdue_regulation = Regulation.objects.create(
            title="Overdue",
            type=Regulation.RegulationType.LINK,
            external_url="https://example.com/overdue",
            is_active=True,
            read_deadline_at=timezone.now() - timezone.timedelta(days=1),
        )
        self.client.force_authenticate(self.employee)
        response = self.client.get(reverse("regulations-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = next(i for i in response.data if i["id"] == str(overdue_regulation.id))
        self.assertTrue(item["is_overdue"])

    def test_public_detail_is_read_only(self):
        self.client.force_authenticate(self.employee)
        url = reverse("regulations-detail", kwargs={"id": self.active_ru.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        patch_response = self.client.patch(
            url,
            {"title": "Nope"},
            format="json",
        )
        self.assertEqual(patch_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_acknowledge_regulation_creates_record_and_is_idempotent(self):
        self.client.force_authenticate(self.employee)
        url = reverse("regulations-acknowledge", kwargs={"id": self.active_ru.id})

        first = self.client.post(url)
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            RegulationAcknowledgement.objects.filter(
                user=self.employee,
                regulation=self.active_ru,
            ).exists()
        )

        second = self.client.post(url)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(
            RegulationAcknowledgement.objects.filter(
                user=self.employee,
                regulation=self.active_ru,
            ).count(),
            1,
        )

    def test_first_day_mandatory_list_contains_ack_status(self):
        self.active_ru.is_mandatory_on_day_one = True
        self.active_ru.save(update_fields=["is_mandatory_on_day_one"])

        self.client.force_authenticate(self.employee)
        url = reverse("regulations-first-day-mandatory")
        response = self.client.get(url, {"language": "ru"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["required_count"], 1)
        self.assertEqual(response.data["acknowledged_count"], 0)


class InternOnboardingFlowTests(APITestCase):
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
        self.employee_role, _ = Role.objects.get_or_create(
            name=Role.Name.EMPLOYEE,
            defaults={"level": Role.Level.EMPLOYEE},
        )
        self.intern = User.objects.create_user(
            username="intern_flow",
            password="StrongPass123!",
            role=self.intern_role,
        )
        self.admin = User.objects.create_user(
            username="admin_flow",
            password="StrongPass123!",
            role=self.admin_role,
        )
        self.department = Department.objects.create(name="QA")
        self.regulation = Regulation.objects.create(
            title="Reg 1",
            description="d",
            type=Regulation.RegulationType.LINK,
            external_url="https://example.com",
            is_active=True,
        )
        self.quiz = RegulationQuiz.objects.create(
            regulation=self.regulation,
            title="Mini test",
            passing_score=100,
            is_active=True,
        )
        self.question = RegulationQuizQuestion.objects.create(
            quiz=self.quiz,
            text="Q1",
            position=1,
        )
        self.correct_option = RegulationQuizOption.objects.create(
            question=self.question,
            text="Correct",
            is_correct=True,
            position=1,
        )
        self.wrong_option = RegulationQuizOption.objects.create(
            question=self.question,
            text="Wrong",
            is_correct=False,
            position=2,
        )

    def test_intern_can_mark_read_and_submit_completion(self):
        self.client.force_authenticate(self.intern)
        read_response = self.client.post(f"/api/v1/regulations/{self.regulation.id}/read/")
        self.assertEqual(read_response.status_code, 200)
        self.assertTrue(
            RegulationReadProgress.objects.filter(
                user=self.intern,
                regulation=self.regulation,
                is_read=True,
            ).exists()
        )

        blocked_submit = self.client.post("/api/v1/regulations/intern/submit/")
        self.assertEqual(blocked_submit.status_code, 400)

        quiz_submit = self.client.post(
            f"/api/v1/regulations/{self.regulation.id}/quiz/submit/",
            {"answers": {str(self.question.id): self.correct_option.id}},
            format="json",
        )
        self.assertEqual(quiz_submit.status_code, 201)
        self.assertTrue(quiz_submit.data["result"]["passed"])

        still_blocked_submit = self.client.post("/api/v1/regulations/intern/submit/")
        self.assertEqual(still_blocked_submit.status_code, 400)
        self.assertIn("missing_report_regulation_ids", still_blocked_submit.data)

        report_submit = self.client.post(
            f"/api/v1/regulations/{self.regulation.id}/read-report/",
            {"report_text": "Сегодня изучил регламент и основные пункты."},
            format="json",
        )
        self.assertIn(report_submit.status_code, {200, 201})
        self.assertTrue(
            RegulationReadReport.objects.filter(
                user=self.intern,
                regulation=self.regulation,
            ).exists()
        )

        submit_response = self.client.post("/api/v1/regulations/intern/submit/")
        self.assertEqual(submit_response.status_code, 201)
        self.assertTrue(
            InternOnboardingRequest.objects.filter(
                user=self.intern,
                status=InternOnboardingRequest.Status.PENDING,
            ).exists()
        )

    def test_quiz_detail_returns_questions_and_options(self):
        self.client.force_authenticate(self.intern)
        response = self.client.get(f"/api/v1/regulations/{self.regulation.id}/quiz/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.quiz.id)
        self.assertEqual(len(response.data["questions"]), 1)

    def test_intern_can_submit_read_report_only_after_read(self):
        self.client.force_authenticate(self.intern)
        before_read = self.client.post(
            f"/api/v1/regulations/{self.regulation.id}/read-report/",
            {"report_text": "report"},
            format="json",
        )
        self.assertEqual(before_read.status_code, 400)

        self.client.post(f"/api/v1/regulations/{self.regulation.id}/read/")
        after_read = self.client.post(
            f"/api/v1/regulations/{self.regulation.id}/read-report/",
            {"report_text": "изучил регламент"},
            format="json",
        )
        self.assertIn(after_read.status_code, {200, 201})

    def test_admin_can_approve_and_promote_to_employee(self):
        request_obj = InternOnboardingRequest.objects.create(user=self.intern)

        self.client.force_authenticate(self.admin)
        response = self.client.post(
            f"/api/v1/regulations/admin/intern-requests/{request_obj.id}/approve/",
            {"department_id": self.department.id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        self.intern.refresh_from_db()
        request_obj.refresh_from_db()
        self.assertEqual(self.intern.role.name, self.employee_role.name)
        self.assertEqual(self.intern.department_id, self.department.id)
        self.assertEqual(request_obj.status, InternOnboardingRequest.Status.APPROVED)
