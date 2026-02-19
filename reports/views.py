
from django.shortcuts import get_object_or_404

from rest_framework import status as drf_status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import OnboardingReport, ReportNotification, OnboardingReportLog
from .serializers import (
    OnboardingReportCreateSerializer,
    AdminOnboardingReportSerializer,
    ReportNotificationSerializer,
    OnboardingReportLogSerializer,
)

from accounts.permissions import HasPermission
from onboarding_core.models import OnboardingDay
from onboarding_core.utils import is_deadline_passed


# =====================================================
# USER: Отправка отчёта
# =====================================================

class SubmitOnboardingReportView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = OnboardingReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        day = get_object_or_404(
            OnboardingDay,
            id=serializer.validated_data["day_id"],
            is_active=True,
        )

        if is_deadline_passed(day):
            return Response(
                {"detail": "Report deadline has passed"},
                status=drf_status.HTTP_403_FORBIDDEN,
            )

        did = serializer.validated_data.get("did", "").strip()
        will_do = serializer.validated_data.get("will_do", "").strip()
        problems = serializer.validated_data.get("problems", "").strip()

        existing_report = OnboardingReport.objects.filter(
            user=request.user,
            day=day,
        ).first()

        if existing_report and not existing_report.can_be_modified():
            return Response(
                {"detail": "Report cannot be modified"},
                status=drf_status.HTTP_409_CONFLICT,
            )

        if existing_report:
            existing_report.did = did
            existing_report.will_do = will_do
            existing_report.problems = problems

            if not existing_report.can_be_sent():
                existing_report.status = OnboardingReport.Status.DRAFT
                existing_report.save(update_fields=["status"])
            else:
                existing_report.send()

            return Response(
                {
                    "id": existing_report.id,
                    "status": existing_report.status,
                }
            )

        # Новый отчёт
        # Новый отчёт
        report = OnboardingReport.objects.create(
            user=request.user,
            day=day,
            did=did,
            will_do=will_do,
            problems=problems,
        )

        OnboardingReportLog.objects.create(
            report=report,
            action=OnboardingReportLog.Action.CREATED,
            author=request.user,
        )

        if report.can_be_sent():
            report.send()
        else:
            report.status = OnboardingReport.Status.DRAFT
            report.save(update_fields=["status"])

        return Response(
            {
                "id": report.id,
                "status": report.status,
            },
            status=drf_status.HTTP_201_CREATED,
        )


# =====================================================
# ADMIN: Работа с отчётами
# =====================================================

class AdminOnboardingReportViewSet(ModelViewSet):
    queryset = OnboardingReport.objects.all()
    serializer_class = AdminOnboardingReportSerializer
    permission_classes = [IsAuthenticated, HasPermission]
    required_permission = "reports_review"
    http_method_names = ["get", "patch"]

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()

        new_status = request.data.get("status")
        comment = request.data.get("reviewer_comment")

        instance.set_status(
            new_status=new_status,
            reviewer=request.user,
            comment=comment,
        )

        serializer = self.get_serializer(instance)
        return Response(serializer.data)


# =====================================================
# LOGS
# =====================================================

class OnboardingReportLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OnboardingReportLogSerializer
    permission_classes = [IsAuthenticated, HasPermission]
    required_permission = "logs_read"

    def get_queryset(self):
        return OnboardingReportLog.objects.select_related(
            "report", "author"
        )


# =====================================================
# NOTIFICATIONS
# =====================================================

class ReportNotificationViewSet(viewsets.ModelViewSet):
    serializer_class = ReportNotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ReportNotification.objects.filter(
            report__user=self.request.user
        )
