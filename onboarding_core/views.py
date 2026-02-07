from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as drf_status
from rest_framework.viewsets import ModelViewSet

from common.permissions import IsAdminOrSuperAdmin

from .models import (
    OnboardingDay,
    OnboardingMaterial,
    OnboardingProgress,
)
from .serializers import (
    OnboardingDayListSerializer,
    OnboardingDayDetailSerializer,
    OnboardingProgressSerializer,
    AdminOnboardingDaySerializer,
    AdminOnboardingMaterialSerializer,
    AdminOnboardingProgressSerializer,
)

# =====================================================
# USER API
# =====================================================

class OnboardingDayListView(ListAPIView):
    """
    Список активных онбординг-дней для стажёра
    """
    permission_classes = [IsAuthenticated]
    serializer_class = OnboardingDayListSerializer

    def get_queryset(self):
        return (
            OnboardingDay.objects
            .filter(is_active=True)
            .order_by("position", "day_number")
        )


class OnboardingDayDetailView(RetrieveAPIView):
    """
    Детали онбординг-дня + материалы.
    Доступ к материалам зависит от статуса дня.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = OnboardingDayDetailSerializer
    lookup_field = "id"

    def get_queryset(self):
        return (
            OnboardingDay.objects
            .filter(is_active=True)
            .prefetch_related("materials")
        )

    def get_serializer_context(self):
        return {"request": self.request}


class CompleteOnboardingDayView(APIView):
    """
    Завершение онбординг-дня.
    Нельзя:
    - пропускать предыдущий день
    - завершать день повторно
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        day = get_object_or_404(OnboardingDay, id=id, is_active=True)

        previous_day = (
            OnboardingDay.objects
            .filter(day_number__lt=day.day_number, is_active=True)
            .order_by("-day_number")
            .first()
        )

        if previous_day:
            prev_progress = OnboardingProgress.objects.filter(
                user=request.user,
                day=previous_day,
                status=OnboardingProgress.Status.DONE,
            ).exists()

            if not prev_progress:
                return Response(
                    {
                        "detail": "Previous onboarding day is not completed",
                        "required_day": previous_day.day_number,
                    },
                    status=drf_status.HTTP_400_BAD_REQUEST,
                )

        progress, created = OnboardingProgress.objects.get_or_create(
            user=request.user,
            day=day,
        )

        if not created and progress.status == OnboardingProgress.Status.DONE:
            return Response(
                {"detail": "Day already completed"},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        progress.status = OnboardingProgress.Status.DONE
        progress.completed_at = timezone.now()
        progress.save()

        return Response(
            {
                "day_id": str(day.id),
                "status": progress.status,
                "completed_at": progress.completed_at,
            },
            status=drf_status.HTTP_200_OK,
        )


class OnboardingOverviewView(APIView):
    """
    Финальный обзор онбординга для стажёра:
    - общий прогресс
    - текущий день
    - статусы всех дней
    """
    permission_classes = [IsAuthenticated]

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
        locked = False

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

            if not locked:
                current_day = day
                locked = True
                result_days.append({
                    "day_id": str(day.id),
                    "day_number": day.day_number,
                    "status": "IN_PROGRESS",
                })
            else:
                result_days.append({
                    "day_id": str(day.id),
                    "day_number": day.day_number,
                    "status": "LOCKED",
                    "locked_reason": "Complete previous day first",
                })

        total_days = days.count()
        progress_percent = (
            int((completed_days / total_days) * 100)
            if total_days else 0
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


# =====================================================
# ADMIN API
# =====================================================

class AdminOnboardingDayViewSet(ModelViewSet):
    """
    Админ: CRUD онбординг-дней
    """
    queryset = (
        OnboardingDay.objects
        .all()
        .order_by("position", "day_number")
    )
    serializer_class = AdminOnboardingDaySerializer
    permission_classes = [IsAdminOrSuperAdmin]
    filterset_fields = ["is_active"]
    ordering_fields = ["position", "day_number"]


class AdminOnboardingMaterialViewSet(ModelViewSet):
    """
    Админ: управление материалами онбординга
    """
    queryset = (
        OnboardingMaterial.objects
        .all()
        .order_by("position")
    )
    serializer_class = AdminOnboardingMaterialSerializer
    permission_classes = [IsAdminOrSuperAdmin]


class AdminOnboardingProgressViewSet(ModelViewSet):
    """
    Админ: просмотр прогресса стажёров (READ ONLY)
    """
    permission_classes = [IsAdminOrSuperAdmin]
    serializer_class = AdminOnboardingProgressSerializer
    http_method_names = ["get"]

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
