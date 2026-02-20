from django.test import TestCase
from rest_framework.test import APIClient

from .models import PasswordResetToken, Role, User


class PasswordResetApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.role, _ = Role.objects.get_or_create(
            name=Role.Name.EMPLOYEE,
            defaults={"level": Role.Level.EMPLOYEE},
        )
        self.user = User.objects.create_user(
            username="employee1",
            email="employee1@example.com",
            password="OldPass123!",
            role=self.role,
        )

    def test_request_creates_token_for_existing_user(self):
        response = self.client.post(
            "/api/v1/accounts/password-reset/request/",
            {"username_or_email": "employee1"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(PasswordResetToken.objects.filter(user=self.user).exists())

    def test_confirm_resets_password(self):
        token = PasswordResetToken.objects.create(user=self.user)

        response = self.client.post(
            "/api/v1/accounts/password-reset/confirm/",
            {"token": str(token.token), "new_password": "NewPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPass123!"))

        token.refresh_from_db()
        self.assertTrue(token.is_used)
