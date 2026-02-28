from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Role, User

from .models import ProcessTemplate, StepTemplate


class BpmApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_role, _ = Role.objects.get_or_create(name=Role.Name.ADMIN, defaults={"level": Role.Level.ADMIN})
        self.employee_role, _ = Role.objects.get_or_create(
            name=Role.Name.EMPLOYEE,
            defaults={"level": Role.Level.EMPLOYEE},
        )
        self.admin = User.objects.create_user(username="bpm_admin", password="StrongPass123!", role=self.admin_role)
        self.employee = User.objects.create_user(
            username="bpm_employee",
            password="StrongPass123!",
            role=self.employee_role,
        )
        self.template = ProcessTemplate.objects.create(name="Hiring", is_active=True)
        self.step = StepTemplate.objects.create(
            process_template=self.template,
            name="Collect docs",
            order=1,
            role_responsible=Role.Name.EMPLOYEE,
            requires_comment=False,
        )

    def test_employee_can_create_instance(self):
        self.client.force_authenticate(self.employee)
        response = self.client.post("/api/v1/bpm/instances/", {"template_id": self.template.id}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "in_progress")

    def test_admin_can_manage_templates(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/v1/bpm/admin/templates/")
        self.assertEqual(response.status_code, 200)
