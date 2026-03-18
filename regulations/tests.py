from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import Role
from regulations.models import (
    Regulation,
    RegulationAcknowledgement,
    RegulationKnowledgeCheck,
    RegulationReadProgress,
)


class RegulationsApiTests(APITestCase):
    def setUp(self):
        self.role_admin, _ = Role.objects.get_or_create(name=Role.Name.ADMIN, defaults={"level": Role.Level.ADMIN})
        self.role_employee, _ = Role.objects.get_or_create(name=Role.Name.EMPLOYEE, defaults={"level": Role.Level.EMPLOYEE})
        self.role_intern, _ = Role.objects.get_or_create(name=Role.Name.INTERN, defaults={"level": Role.Level.INTERN})

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
        self.intern = user_model.objects.create_user(
            username="reg_intern",
            password="StrongPass123!",
            role=self.role_intern,
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
        self.assertIn("external_url", (bad_response.data.get("errors") or {}))

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

    def test_public_list_action_is_download_for_files(self):
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
        self.assertEqual(response.data[0]["action"], "download")

    def test_acknowledge_regulation_is_idempotent(self):
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
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["required_count"], 1)
        self.assertEqual(response.data["acknowledged_count"], 0)

    def test_intern_can_mark_read_and_submit_quiz(self):
        reg = Regulation.objects.create(
            title="Quiz reg",
            type=Regulation.RegulationType.LINK,
            external_url="https://example.com/quiz",
            is_active=True,
            language=Regulation.Language.RU,
            quiz_questions=[
                {"question": "Q1", "options": ["a", "b"], "correct_answer": "a", "tags": ["Тест"]},
                {"question": "Q2", "options": ["x", "y"], "correct_answer": "x", "tags": ["Тест"]},
            ],
            quiz_allowed_mistakes=0,
        )

        self.client.force_authenticate(self.intern)
        read_response = self.client.post(reverse("regulation-read", kwargs={"regulation_id": reg.id}))
        self.assertEqual(read_response.status_code, 200)
        self.assertTrue(RegulationReadProgress.objects.filter(user=self.intern, regulation=reg, is_read=True).exists())

        quiz_resp = self.client.post(
            reverse("regulation-quiz", kwargs={"regulation_id": reg.id}),
            {"answers": ["a", "x"]},
            format="json",
        )
        self.assertEqual(quiz_resp.status_code, 200)
        self.assertTrue(quiz_resp.data["is_passed"])
        self.assertTrue(RegulationKnowledgeCheck.objects.filter(user=self.intern, regulation=reg, is_passed=True).exists())
