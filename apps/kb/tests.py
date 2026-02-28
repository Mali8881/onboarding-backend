from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Role, User

from .models import KBArticle, KBCategory


class KbApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_role, _ = Role.objects.get_or_create(name=Role.Name.ADMIN, defaults={"level": Role.Level.ADMIN})
        self.employee_role, _ = Role.objects.get_or_create(
            name=Role.Name.EMPLOYEE,
            defaults={"level": Role.Level.EMPLOYEE},
        )
        self.admin = User.objects.create_user(username="kb_admin", password="StrongPass123!", role=self.admin_role)
        self.employee = User.objects.create_user(
            username="kb_employee",
            password="StrongPass123!",
            role=self.employee_role,
        )
        self.category = KBCategory.objects.create(name="Rules")
        self.article = KBArticle.objects.create(
            title="Safety",
            content="Use helmet",
            category=self.category,
            visibility=KBArticle.Visibility.ALL,
            is_published=True,
            created_by=self.admin,
        )

    def test_employee_can_view_published_articles(self):
        self.client.force_authenticate(self.employee)
        response = self.client.get("/api/v1/kb/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_article_detail_creates_view_log(self):
        self.client.force_authenticate(self.employee)
        response = self.client.get(f"/api/v1/kb/{self.article.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.article.view_logs.count(), 1)
