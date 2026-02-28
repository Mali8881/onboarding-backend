from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Role, User


class MetricsApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.teamlead_role, _ = Role.objects.get_or_create(
            name=Role.Name.TEAMLEAD,
            defaults={"level": Role.Level.TEAMLEAD},
        )
        self.employee_role, _ = Role.objects.get_or_create(
            name=Role.Name.EMPLOYEE,
            defaults={"level": Role.Level.EMPLOYEE},
        )
        self.teamlead = User.objects.create_user(
            username="metrics_teamlead",
            password="StrongPass123!",
            role=self.teamlead_role,
        )
        self.member = User.objects.create_user(
            username="metrics_member",
            password="StrongPass123!",
            role=self.employee_role,
            manager=self.teamlead,
        )

    def test_my_metrics_available(self):
        self.client.force_authenticate(self.member)
        response = self.client.get("/api/v1/metrics/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("tasks_created_7d", response.data)

    def test_team_metrics_available_for_teamlead(self):
        self.client.force_authenticate(self.teamlead)
        response = self.client.get("/api/v1/metrics/team/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["team_size"], 1)
