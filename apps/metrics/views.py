from calendar import monthrange
from datetime import date
from datetime import timedelta

from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.access_policy import AccessPolicy
from accounts.models import Role, User
from apps.attendance.models import AttendanceMark, WorkCalendarDay
from apps.kb.models import KBViewLog
from apps.tasks.models import Task
from onboarding_core.models import OnboardingDay, OnboardingProgress


CLOSED_COLUMN_NAMES = {"done", "completed", "closed", "завершено"}


def _is_closed_task(task):
    return task.column.name.strip().lower() in CLOSED_COLUMN_NAMES


def _planned_days(year: int, month: int) -> int:
    count = WorkCalendarDay.objects.filter(date__year=year, date__month=month, is_working_day=True).count()
    if count:
        return count
    return sum(1 for day in range(1, monthrange(year, month)[1] + 1) if date(year, month, day).weekday() < 5)


def _attendance_percent_for_users(user_ids, year: int, month: int) -> float:
    if not user_ids:
        return 0.0
    worked = AttendanceMark.objects.filter(
        user_id__in=user_ids,
        date__year=year,
        date__month=month,
        status__in=[AttendanceMark.Status.PRESENT, AttendanceMark.Status.REMOTE],
    ).count()
    planned = _planned_days(year, month) * len(user_ids)
    if not planned:
        return 0.0
    return round((worked / planned) * 100, 2)


def _onboarding_percent_for_users(user_ids) -> float:
    if not user_ids:
        return 0.0
    intern_ids = list(User.objects.filter(id__in=user_ids, role__name=Role.Name.INTERN).values_list("id", flat=True))
    if not intern_ids:
        return 0.0
    total_days = OnboardingDay.objects.filter(is_active=True).count()
    if not total_days:
        return 0.0
    done_count = OnboardingProgress.objects.filter(
        user_id__in=intern_ids,
        status=OnboardingProgress.Status.DONE,
        day__is_active=True,
    ).count()
    max_possible = len(intern_ids) * total_days
    return round((done_count / max_possible) * 100, 2) if max_possible else 0.0


class MetricsMyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        since = now - timedelta(days=7)
        user = request.user

        my_tasks = Task.objects.select_related("column").filter(assignee=user)
        created_7 = my_tasks.filter(created_at__gte=since).count()
        closed_7 = sum(1 for task in my_tasks.filter(updated_at__gte=since) if _is_closed_task(task))
        overdue = sum(1 for task in my_tasks if task.due_date and task.due_date < now.date() and not _is_closed_task(task))

        attendance_percent = _attendance_percent_for_users([user.id], now.year, now.month)
        kb_views = KBViewLog.objects.filter(user=user, viewed_at__year=now.year, viewed_at__month=now.month).count()
        onboarding_percent = _onboarding_percent_for_users([user.id])

        return Response(
            {
                "tasks_created_7d": created_7,
                "tasks_closed_7d": closed_7,
                "tasks_overdue": overdue,
                "attendance_percent_month": attendance_percent,
                "kb_views_month": kb_views,
                "onboarding_progress_percent": onboarding_percent,
            }
        )


class MetricsTeamAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not (AccessPolicy.is_admin_like(request.user) or AccessPolicy.is_teamlead(request.user)):
            return Response({"detail": "Access denied."}, status=403)
        now = timezone.now()
        since = now - timedelta(days=7)

        if AccessPolicy.is_admin_like(request.user):
            team_ids = list(User.objects.filter(is_active=True).exclude(role__name=Role.Name.SUPER_ADMIN).values_list("id", flat=True))
        else:
            team_ids = list(request.user.team_members.values_list("id", flat=True))

        tasks = Task.objects.select_related("column").filter(assignee_id__in=team_ids)
        created_7 = tasks.filter(created_at__gte=since).count()
        closed_7 = sum(1 for task in tasks.filter(updated_at__gte=since) if _is_closed_task(task))
        overdue = sum(1 for task in tasks if task.due_date and task.due_date < now.date() and not _is_closed_task(task))

        attendance_percent = _attendance_percent_for_users(team_ids, now.year, now.month)
        kb_views = KBViewLog.objects.filter(
            user_id__in=team_ids,
            viewed_at__year=now.year,
            viewed_at__month=now.month,
        ).count()
        onboarding_percent = _onboarding_percent_for_users(team_ids)

        return Response(
            {
                "team_size": len(team_ids),
                "tasks_created_7d": created_7,
                "tasks_closed_7d": closed_7,
                "tasks_overdue": overdue,
                "attendance_percent_month": attendance_percent,
                "kb_views_month": kb_views,
                "onboarding_progress_percent": onboarding_percent,
            }
        )
