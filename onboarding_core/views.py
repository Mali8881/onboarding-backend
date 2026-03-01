from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status as drf_status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView

from accounts.permissions import HasPermission
from accounts.models import Role
from apps.audit import AuditEvents, log_event
from apps.tasks.models import Board, Column, Task
from regulations.models import (
    Regulation,
    RegulationAcknowledgement,
    RegulationFeedback,
    RegulationKnowledgeCheck,
    RegulationReadProgress,
)

from .models import OnboardingDay, OnboardingMaterial, OnboardingProgress
from .audit import OnboardingAuditService
from .serializers import (
    AdminOnboardingDaySerializer,
    AdminOnboardingMaterialSerializer,
    AdminOnboardingProgressSerializer,
    OnboardingDayDetailSerializer,
    OnboardingDayListSerializer,
)


def _get_user_default_board(user) -> Board:
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


def _get_day_one_regulations_queryset(day):
    if day.day_number == 1:
        return Regulation.objects.filter(is_active=True).order_by("position", "-created_at")
    return day.regulations.filter(is_active=True).order_by("position", "-created_at")


def _ensure_day_one_onboarding_task_for_intern(*, user, day):
    if not (getattr(user, "role_id", None) and user.role.name == Role.Name.INTERN):
        return
    if day.day_number != 1:
        return

    existing = Task.objects.filter(assignee=user, onboarding_day=day).first()
    if existing is not None:
        return

    board = _get_user_default_board(user)
    column = board.columns.order_by("order", "id").first()
    if column is None:
        column = Column.objects.create(board=board, name="New", order=1)

    today = timezone.localdate()
    due_date = today + timedelta(days=1)
    regulation_titles = list(_get_day_one_regulations_queryset(day).values_list("title", flat=True))
    regulations_block = (
        "\n".join(f"- {title}" for title in regulation_titles)
        if regulation_titles
        else "- Регламенты будут добавлены администратором."
    )
    description = (
        "Цель этого дня: ознакомление с регламентами компании.\n"
        "Дедлайн: один день (до следующего дня с момента открытия задачи).\n\n"
        "Задача: прочитать все регламенты.\n\n"
        "Регламенты:\n"
        f"{regulations_block}\n\n"
        "После ознакомления отправьте отчет (стендап) во вкладке отчета."
    )

    Task.objects.create(
        board=board,
        column=column,
        title="День 1: Ознакомление с регламентами компании",
        description=description,
        assignee=user,
        reporter=user.manager if user.manager_id else user,
        onboarding_day=day,
        due_date=due_date,
        priority=Task.Priority.HIGH,
    )

class OnboardingDayListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OnboardingDayListSerializer

    def get_queryset(self):
        return (
            OnboardingDay.objects
            .filter(is_active=True)
            .order_by("position", "day_number")
        )


class OnboardingDayDetailView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OnboardingDayDetailSerializer
    lookup_field = "id"

    def get_queryset(self):
        return (
            OnboardingDay.objects
            .filter(is_active=True)
            .prefetch_related("materials", "regulations")
        )

    def get_serializer_context(self):
        return {"request": self.request}

    def retrieve(self, request, *args, **kwargs):
        day = self.get_object()
        _ensure_day_one_onboarding_task_for_intern(user=request.user, day=day)
        serializer = self.get_serializer(day)
        return Response(serializer.data)


class CompleteOnboardingDayView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="Marks onboarding day as completed for current user.",
        responses={
            200: OpenApiResponse(description="Day marked as completed"),
            401: OpenApiResponse(description="Unauthorized"),
            404: OpenApiResponse(description="Day not found"),
        },
    )
    def post(self, request, id):
        day = get_object_or_404(OnboardingDay, id=id, is_active=True)

        if (
            getattr(request.user, "role_id", None)
            and request.user.role.name == Role.Name.INTERN
            and day.day_number == 1
        ):
            mandatory = Regulation.objects.filter(
                is_active=True,
                is_mandatory_on_day_one=True,
            )
            if mandatory.exists():
                acknowledged_ids = set(
                    RegulationAcknowledgement.objects.filter(
                        user=request.user,
                        regulation__in=mandatory,
                    ).values_list("regulation_id", flat=True)
                )
                missing = mandatory.exclude(id__in=acknowledged_ids)
                if missing.exists():
                    missing_docs = list(missing.values("id", "title"))
                    log_event(
                        action=AuditEvents.ONBOARDING_DAY1_BLOCKED_MISSING_REGULATIONS,
                        actor=request.user,
                        object_type="onboarding_day",
                        object_id=str(day.id),
                        category="content",
                        level="warning",
                        ip_address=request.META.get("REMOTE_ADDR"),
                        metadata={
                            "missing_count": len(missing_docs),
                            "missing_docs": [
                                {"id": str(item["id"]), "title": item["title"]}
                                for item in missing_docs
                            ],
                        },
                    )
                    return Response(
                        {
                            "detail": "Нельзя завершить 1-й день: подтвердите ознакомление с обязательными регламентами.",
                            "missing_regulations": [
                                {"id": str(item["id"]), "title": item["title"]}
                                for item in missing_docs
                            ],
                        },
                        status=drf_status.HTTP_409_CONFLICT,
                    )

            day_regs = list(_get_day_one_regulations_queryset(day))
            if day_regs:
                reg_ids = [reg.id for reg in day_regs]
                read_ids = set(
                    RegulationReadProgress.objects.filter(
                        user=request.user,
                        regulation_id__in=reg_ids,
                        is_read=True,
                    ).values_list("regulation_id", flat=True)
                )
                feedback_ids = set(
                    RegulationFeedback.objects.filter(
                        user=request.user,
                        regulation_id__in=reg_ids,
                    ).values_list("regulation_id", flat=True)
                )
                quiz_ids = set(
                    RegulationKnowledgeCheck.objects.filter(
                        user=request.user,
                        regulation_id__in=reg_ids,
                        is_passed=True,
                    ).values_list("regulation_id", flat=True)
                )

                missing_steps = []
                for reg in day_regs:
                    steps = []
                    if reg.id not in read_ids:
                        steps.append("read")
                    if reg.id not in feedback_ids:
                        steps.append("feedback")
                    if reg.id not in quiz_ids:
                        steps.append("quiz")
                    if steps:
                        missing_steps.append(
                            {
                                "id": str(reg.id),
                                "title": reg.title,
                                "missing": steps,
                            }
                        )

                if missing_steps:
                    return Response(
                        {
                            "detail": "Нельзя завершить 1-й день: для каждого регламента нужны шаги 'прочитал', 'фидбек' и 'тест'.",
                            "missing_steps": missing_steps,
                        },
                        status=drf_status.HTTP_409_CONFLICT,
                    )

        progress, created = OnboardingProgress.objects.get_or_create(
            user=request.user,
            day=day,
        )

        if not created and progress.status == OnboardingProgress.Status.DONE:
            OnboardingAuditService.log_day_completed(
                request,
                day,
                progress.completed_at,
                idempotent=True,
            )
            return Response(
                {
                    "day_id": str(day.id),
                    "status": progress.status,
                    "completed_at": progress.completed_at,
                },
                status=drf_status.HTTP_200_OK,
            )

        progress.status = OnboardingProgress.Status.DONE
        progress.completed_at = timezone.now()
        progress.save(update_fields=["status", "completed_at", "updated_at"])
        OnboardingAuditService.log_day_completed(
            request,
            day,
            progress.completed_at,
            idempotent=False,
        )

        return Response(
            {
                "day_id": str(day.id),
                "status": progress.status,
                "completed_at": progress.completed_at,
            },
            status=drf_status.HTTP_200_OK,
        )


class OnboardingOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="Onboarding summary for current user.",
        responses={
            200: OpenApiResponse(description="Onboarding summary"),
            401: OpenApiResponse(description="Unauthorized"),
        },
    )
    def get(self, request):
        user = request.user

        days = (
            OnboardingDay.objects
            .filter(is_active=True)
            .order_by("position", "day_number")
        )

        progress_qs = OnboardingProgress.objects.filter(user=user)
        progress_map = {p.day_id: p for p in progress_qs}

        completed_days = 0
        result_days = []
        current_day = None

        for day in days:
            progress = progress_map.get(day.id)

            if progress and progress.status == OnboardingProgress.Status.DONE:
                completed_days += 1
                result_days.append({
                    "day_id": str(day.id),
                    "day_number": day.day_number,
                    "status": "DONE",
                })
                continue

            if current_day is None:
                current_day = day

            result_days.append({
                "day_id": str(day.id),
                "day_number": day.day_number,
                "status": "IN_PROGRESS",
            })

        total_days = days.count()
        progress_percent = int((completed_days / total_days) * 100) if total_days else 0
        OnboardingAuditService.log_overview_viewed(
            request,
            total_days=total_days,
            completed_days=completed_days,
            progress_percent=progress_percent,
        )

        return Response({
            "total_days": total_days,
            "completed_days": completed_days,
            "progress_percent": progress_percent,
            "current_day": (
                {
                    "id": str(current_day.id),
                    "day_number": current_day.day_number,
                    "title": current_day.title,
                } if current_day else None
            ),
            "days": result_days,
        })


class AdminOnboardingDayViewSet(ModelViewSet):
    queryset = (
        OnboardingDay.objects
        .all()
        .order_by("position", "day_number")
    )
    serializer_class = AdminOnboardingDaySerializer
    permission_classes = [IsAuthenticated, HasPermission]
    required_permission = "onboarding_manage"

    filterset_fields = ["is_active"]
    ordering_fields = ["position", "day_number"]

    def perform_create(self, serializer):
        day = serializer.save()
        OnboardingAuditService.log_day_created(self.request, day)

    def perform_update(self, serializer):
        day = serializer.save()
        changed_fields = sorted(serializer.validated_data.keys())
        OnboardingAuditService.log_day_updated(self.request, day, changed_fields)

    def perform_destroy(self, instance):
        day = instance
        OnboardingAuditService.log_day_deleted(self.request, day)
        super().perform_destroy(instance)


class AdminOnboardingMaterialViewSet(ModelViewSet):
    queryset = (
        OnboardingMaterial.objects
        .all()
        .order_by("position")
    )
    serializer_class = AdminOnboardingMaterialSerializer
    permission_classes = [IsAuthenticated, HasPermission]
    required_permission = "onboarding_manage"

    def perform_create(self, serializer):
        material = serializer.save()
        OnboardingAuditService.log_material_created(self.request, material)

    def perform_update(self, serializer):
        material = serializer.save()
        changed_fields = sorted(serializer.validated_data.keys())
        OnboardingAuditService.log_material_updated(self.request, material, changed_fields)

    def perform_destroy(self, instance):
        material = instance
        OnboardingAuditService.log_material_deleted(self.request, material)
        super().perform_destroy(instance)


class AdminOnboardingProgressViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, HasPermission]
    required_permission = "reports_review"
    serializer_class = AdminOnboardingProgressSerializer
    http_method_names = ["get"]

    def list(self, request, *args, **kwargs):
        filters = {
            "user_id": request.query_params.get("user_id"),
            "status": request.query_params.get("status"),
            "day_number": request.query_params.get("day_number"),
        }
        OnboardingAuditService.log_progress_viewed_admin(request, filters)
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        qs = (
            OnboardingProgress.objects
            .select_related("user", "day")
            .order_by("user_id", "day__day_number")
        )

        user_id = self.request.query_params.get("user_id")
        status = self.request.query_params.get("status")
        day_number = self.request.query_params.get("day_number")

        if user_id:
            qs = qs.filter(user_id=user_id)

        if status:
            qs = qs.filter(status=status)

        if day_number:
            qs = qs.filter(day__day_number=day_number)

        return qs

