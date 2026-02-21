from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import Role
from regulations.models import Regulation, RegulationAcknowledgement


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
        self.assertEqual(response.data[0]["action"], "download")

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
