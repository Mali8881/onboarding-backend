from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Role, User
from onboarding_core.models import OnboardingDay
from work_schedule.models import WeeklyWorkPlan
from .audit import TasksAuditService
from .models import Board, Column, Task
from .policies import TaskPolicy
from .serializers import TaskCreateSerializer, TaskMoveSerializer, TaskSerializer


MANDATORY_WEEKLY_PLAN_TASK_TITLE = "Сделать график работы на следующую неделю"
DEFAULT_COLUMNS = (
    (1, "Новые"),
    (2, "В работе"),
    (3, "На проверке"),
    (4, "Завершенные"),
)


def _ensure_default_columns(board: Board) -> None:
    for order, name in DEFAULT_COLUMNS:
        Column.objects.get_or_create(
            board=board,
            order=order,
            defaults={"name": name},
        )


def get_user_default_board(user) -> Board:
    board, _ = Board.objects.get_or_create(
        created_by=user,
        is_personal=True,
        defaults={"name": f"{user.username} board"},
    )
    _ensure_default_columns(board)
    return board


def _next_monday(today):
    days_ahead = (7 - today.weekday()) % 7
    return today + timedelta(days=days_ahead or 7)


def _ensure_weekly_plan_task_for_user(*, assignee, reporter):
    next_week_start = _next_monday(timezone.localdate())
    has_plan = WeeklyWorkPlan.objects.filter(user=assignee, week_start=next_week_start).exists()
    if has_plan:
        return None

    exists_task = Task.objects.filter(
        assignee=assignee,
        title=MANDATORY_WEEKLY_PLAN_TASK_TITLE,
        due_date=next_week_start,
    ).exists()
    if exists_task:
        return None

    board = get_user_default_board(assignee)
    column = board.columns.order_by("order", "id").first()
    if column is None:
        column = Column.objects.create(board=board, name="Новые", order=1)
    return Task.objects.create(
        board=board,
        column=column,
        title=MANDATORY_WEEKLY_PLAN_TASK_TITLE,
        description=f"Заполнить и отправить недельный график на неделю с {next_week_start.isoformat()}",
        assignee=assignee,
        reporter=reporter,
        due_date=next_week_start,
        priority=Task.Priority.HIGH,
    )


class TaskMyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        reporter = request.user.manager if request.user.manager_id else request.user
        auto_task = _ensure_weekly_plan_task_for_user(assignee=request.user, reporter=reporter)
        if auto_task is not None:
            TasksAuditService.log_task_created(request, auto_task)
        qs = Task.objects.filter(assignee=request.user).select_related("assignee", "reporter", "column", "board")
        return Response(TaskSerializer(qs, many=True).data)


class TaskTeamAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not TaskPolicy.can_manage_team(request.user):
            return Response({"detail": "Access denied."}, status=status.HTTP_403_FORBIDDEN)

        if TaskPolicy.is_admin_like(request.user):
            team_users = User.objects.filter(
                is_active=True,
                role__name__in=[Role.Name.TEAMLEAD, Role.Name.EMPLOYEE, Role.Name.INTERN],
            )
            qs = Task.objects.all()
            if TaskPolicy.is_department_admin(request.user):
                if request.user.department_id:
                    team_users = team_users.filter(department_id=request.user.department_id)
                    qs = qs.filter(assignee__department_id=request.user.department_id)
        else:
            team_users = request.user.team_members.filter(is_active=True)
            qs = Task.objects.filter(assignee__manager=request.user)

        for user in team_users:
            auto_task = _ensure_weekly_plan_task_for_user(assignee=user, reporter=request.user)
            if auto_task is not None:
                TasksAuditService.log_task_created(request, auto_task)

        qs = qs.select_related("assignee", "reporter", "column", "board")
        return Response(TaskSerializer(qs, many=True).data)


class TaskCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TaskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignee = get_object_or_404(User, id=serializer.validated_data["assignee_id"])

        if not TaskPolicy.can_assign_task(request.user, assignee):
            return Response({"detail": "Access denied."}, status=status.HTTP_403_FORBIDDEN)

        board = get_user_default_board(assignee)
        column = board.columns.order_by("order", "id").first()
        onboarding_day = None
        onboarding_day_id = serializer.validated_data.get("onboarding_day_id")
        if onboarding_day_id:
            onboarding_day = get_object_or_404(OnboardingDay, id=onboarding_day_id)
        task = Task.objects.create(
            board=board,
            column=column,
            title=serializer.validated_data["title"],
            description=serializer.validated_data.get("description", ""),
            assignee=assignee,
            reporter=request.user,
            onboarding_day=onboarding_day,
            due_date=serializer.validated_data.get("due_date"),
            priority=serializer.validated_data.get("priority", Task.Priority.MEDIUM),
        )
        TasksAuditService.log_task_created(request, task)
        return Response(TaskSerializer(task).data, status=status.HTTP_201_CREATED)


class TaskDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        task = get_object_or_404(Task.objects.select_related("assignee", "reporter", "column", "board"), pk=pk)
        if not TaskPolicy.can_view_task(request.user, task):
            return Response({"detail": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
        return Response(TaskSerializer(task).data)

    def patch(self, request, pk):
        task = get_object_or_404(Task.objects.select_related("assignee"), pk=pk)
        if not TaskPolicy.can_edit_task(request.user, task):
            return Response({"detail": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
        serializer = TaskSerializer(task, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        changed_fields = sorted(serializer.validated_data.keys())
        if changed_fields:
            TasksAuditService.log_task_updated(request, task, changed_fields)
        return Response(serializer.data)


class TaskMoveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        task = get_object_or_404(Task.objects.select_related("assignee", "column"), pk=pk)
        if not TaskPolicy.can_edit_task(request.user, task):
            return Response({"detail": "Access denied."}, status=status.HTTP_403_FORBIDDEN)

        serializer = TaskMoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_column = get_object_or_404(Column, id=serializer.validated_data["column_id"])
        if new_column.board_id != task.board_id:
            return Response(
                {"detail": "Column belongs to another board."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_column_id = task.column_id
        task.column = new_column
        task.save(update_fields=["column", "updated_at"])
        TasksAuditService.log_task_moved(request, task, old_column_id, task.column_id)
        return Response(TaskSerializer(task).data)
