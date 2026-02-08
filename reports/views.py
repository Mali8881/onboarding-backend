from django.shortcuts import get_object_or_404

from rest_framework import permissions, status as drf_status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated

from drf_spectacular.utils import extend_schema, OpenApiResponse


from .models import OnboardingReport, ReportNotification
from .serializers import (
    OnboardingReportCreateSerializer,
    AdminOnboardingReportSerializer, ReportNotificationSerializer, OnboardingReportLogSerializer,
)

from accounts.permissions import IsAdminOrSuperAdmin
from onboarding_core.models import OnboardingDay
from onboarding_core.utils import is_deadline_passed



class ReportNotificationViewSet(viewsets.ModelViewSet):
    queryset = ReportNotification.objects.all()
    serializer_class = ReportNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

class SubmitOnboardingReportView(APIView):
    """
    Отправка отчёта стажёром
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="Отправка отчёта стажёром.",
        responses={
            204: OpenApiResponse(description="Отчёт успешно отправлён"),
            400: OpenApiResponse(description="Некорректные данные"),
            401: OpenApiResponse(description="Пользователь не авторизован"),
        },
    )
    def post(self, request):
        serializer = OnboardingReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        day = get_object_or_404(
            OnboardingDay,
            id=serializer.validated_data["day_id"],
            is_active=True,
        )

        # ⏰ Проверка дедлайна
        if is_deadline_passed(day):
            return Response(
                {"detail": "Report deadline has passed"},
                status=drf_status.HTTP_403_FORBIDDEN,
            )

        did = serializer.validated_data.get("did", "").strip()
        will_do = serializer.validated_data.get("will_do", "").strip()
        problems = serializer.validated_data.get("problems", "").strip()

        is_empty_report = not did or not will_do

        existing_report = OnboardingReport.objects.filter(
            user=request.user,
            day=day,
        ).first()

        # ❌ Нельзя пересдавать, если уже SENT / ACCEPTED
        if existing_report and existing_report.status in [
            OnboardingReport.Status.SENT,
            OnboardingReport.Status.ACCEPTED,
        ]:
            return Response(
                {"detail": "Report for this day already exists"},
                status=drf_status.HTTP_409_CONFLICT,
            )

        status = (
            OnboardingReport.Status.REJECTED
            if is_empty_report
            else OnboardingReport.Status.SENT
        )

        # 🔁 Обновление при REVISION / REJECTED
        if existing_report:
            existing_report.did = did
            existing_report.will_do = will_do
            existing_report.problems = problems
            existing_report.status = status
            existing_report.reviewer_comment = ""
            existing_report.save()

            return Response(
                {
                    "id": existing_report.id,
                    "day_id": str(day.id),
                    "status": existing_report.status,
                    "updated_at": existing_report.created_at,
                },
                status=drf_status.HTTP_200_OK,
            )

        # 🆕 Первый отчёт
        report = OnboardingReport.objects.create(
            user=request.user,
            day=day,
            did=did,
            will_do=will_do,
            problems=problems,
            status=status,
        )

        return Response(
            {
                "id": report.id,
                "day_id": str(day.id),
                "status": report.status,
                "created_at": report.created_at,
            },
            status=drf_status.HTTP_201_CREATED,
        )





class AdminOnboardingReportViewSet(ModelViewSet):
    queryset = OnboardingReport.objects.all()
    serializer_class = AdminOnboardingReportSerializer
    permission_classes = [IsAdminOrSuperAdmin]
    http_method_names = ["get", "patch"]

class OnboardingReportLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OnboardingReportLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            return OnboardingReportLog.objects.select_related(
                "report", "author"
            )

        return OnboardingReportLog.objects.filter(
            report__user=user
        ).select_related("report", "author")

class ReportNotificationViewSet(viewsets.ModelViewSet):
    serializer_class = ReportNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            return ReportNotification.objects.all()

        return ReportNotification.objects.filter(
            report__user=user
        )


class OnboardingReportViewSet:
    pass