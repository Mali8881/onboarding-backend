from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .audit import TasksAuditService
from .models import Board, Column, Task
from .policies import TaskPolicy
from .serializers import TaskCreateSerializer, TaskMoveSerializer, TaskSerializer


User = get_user_model()


def get_user_default_board(user) -> Board:
    board, _ = Board.objects.get_or_create(
        created_by=user,
        is_personal=True,
        defaults={"name": f"{user.username} board"},
    )
    Column.objects.get_or_create(
        board=board,
        order=1,
        defaults={"name": "New"},
    )
    return board


class TaskMyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Task.objects.filter(assignee=request.user).select_related("assignee", "reporter", "column", "board")
        return Response(TaskSerializer(qs, many=True).data)


class TaskTeamAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not TaskPolicy.can_manage_team(request.user):
            return Response({"detail": "Access denied."}, status=status.HTTP_403_FORBIDDEN)

        if TaskPolicy.is_admin_like(request.user):
            qs = Task.objects.all()
        else:
            qs = Task.objects.filter(assignee__manager=request.user)

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
        column = board.columns.order_by("order").first()
        task = Task.objects.create(
            board=board,
            column=column,
            title=serializer.validated_data["title"],
            description=serializer.validated_data.get("description", ""),
            assignee=assignee,
            reporter=request.user,
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

