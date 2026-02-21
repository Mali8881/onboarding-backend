from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Role, User

from .models import Column, Task


class TasksApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.employee_role, _ = Role.objects.get_or_create(
            name=Role.Name.EMPLOYEE,
            defaults={"level": Role.Level.EMPLOYEE},
        )
        self.admin_role, _ = Role.objects.get_or_create(
            name=Role.Name.ADMIN,
            defaults={"level": Role.Level.ADMIN},
        )

        self.lead = User.objects.create_user(
            username="lead_task",
            password="StrongPass123!",
            role=self.employee_role,
        )
        self.subordinate = User.objects.create_user(
            username="sub_task",
            password="StrongPass123!",
            role=self.employee_role,
            manager=self.lead,
        )
        self.outsider = User.objects.create_user(
            username="out_task",
            password="StrongPass123!",
            role=self.employee_role,
        )
        self.admin = User.objects.create_user(
            username="admin_task",
            password="StrongPass123!",
            role=self.admin_role,
        )

    @patch("apps.tasks.views.TasksAuditService.log_task_created")
    def test_teamlead_can_create_task_for_subordinate(self, log_task_created):
        self.client.force_authenticate(user=self.lead)
        response = self.client.post(
            "/api/v1/tasks/create/",
            {
                "title": "Task 1",
                "description": "Desc",
                "assignee_id": self.subordinate.id,
                "priority": "medium",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Task.objects.filter(assignee=self.subordinate, reporter=self.lead).exists())
        log_task_created.assert_called_once()

    def test_teamlead_cannot_create_task_for_outside_user(self):
        self.client.force_authenticate(user=self.lead)
        response = self.client.post(
            "/api/v1/tasks/create/",
            {"title": "Task 2", "assignee_id": self.outsider.id},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_my_endpoint_returns_only_assigned_tasks(self):
        task1 = Task.objects.create(
            board=self._create_default_board(self.subordinate),
            column=self._get_new_column(self.subordinate),
            title="Mine",
            assignee=self.subordinate,
            reporter=self.lead,
        )
        Task.objects.create(
            board=self._create_default_board(self.outsider),
            column=self._get_new_column(self.outsider),
            title="Other",
            assignee=self.outsider,
            reporter=self.lead,
        )
        self.client.force_authenticate(user=self.subordinate)
        response = self.client.get("/api/v1/tasks/my/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], task1.id)

    def test_team_endpoint_for_lead_returns_subordinates_tasks(self):
        task = Task.objects.create(
            board=self._create_default_board(self.subordinate),
            column=self._get_new_column(self.subordinate),
            title="Team task",
            assignee=self.subordinate,
            reporter=self.lead,
        )
        Task.objects.create(
            board=self._create_default_board(self.outsider),
            column=self._get_new_column(self.outsider),
            title="Out task",
            assignee=self.outsider,
            reporter=self.lead,
        )
        self.client.force_authenticate(user=self.lead)
        response = self.client.get("/api/v1/tasks/team/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], task.id)

    @patch("apps.tasks.views.TasksAuditService.log_task_moved")
    def test_move_task_logs_audit(self, log_task_moved):
        board = self._create_default_board(self.subordinate)
        col1 = self._get_new_column(self.subordinate)
        col2 = Column.objects.create(board=board, name="In progress", order=2)
        task = Task.objects.create(
            board=board,
            column=col1,
            title="Move me",
            assignee=self.subordinate,
            reporter=self.lead,
        )
        self.client.force_authenticate(user=self.lead)
        response = self.client.patch(f"/api/v1/tasks/{task.id}/move/", {"column_id": col2.id}, format="json")
        self.assertEqual(response.status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.column_id, col2.id)
        log_task_moved.assert_called_once()

    def _create_default_board(self, user):
        from .views import get_user_default_board

        return get_user_default_board(user)

    def _get_new_column(self, user):
        board = self._create_default_board(user)
        return board.columns.order_by("order").first()

