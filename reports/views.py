from django.shortcuts import get_object_or_404

from rest_framework import status as drf_status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from django.utils import timezone

from accounts.access_policy import AccessPolicy
from .models import EmployeeDailyReport, OnboardingReport, OnboardingReportLog, ReportNotification
from .serializers import (
    EmployeeDailyReportSerializer,
    AdminOnboardingReportSerializer,
    OnboardingReportCreateSerializer,
    OnboardingReportLogSerializer,
    ReportNotificationSerializer,
)

from accounts.permissions import HasPermission
from onboarding_core.models import OnboardingDay
from onboarding_core.utils import is_deadline_passed
from .audit import ReportsAuditService


SYSTEM_REJECT_COMMENT = "Report is empty. Fill in 'did' and 'will_do' before submit."


class SubmitOnboardingReportView(APIView):
    permission_classes = [IsAuthenticated]

    def _mark_rejected(self, report):
        report.status = OnboardingReport.Status.REJECTED
        report.reviewer_comment = SYSTEM_REJECT_COMMENT
        report.save(update_fields=["status", "reviewer_comment", "updated_at"])
        OnboardingReportLog.objects.create(
            report=report,
            action=OnboardingReportLog.Action.REJECTED,
            author=None,
        )

    def post(self, request):
        serializer = OnboardingReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        day = get_object_or_404(
            OnboardingDay,
            id=serializer.validated_data["day_id"],
            is_active=True,
        )

        if is_deadline_passed(day):
            ReportsAuditService.log_report_deadline_blocked(request, day)
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
            ReportsAuditService.log_report_edit_conflict(request, existing_report)
            return Response(
                {"detail": "Report cannot be modified"},
                status=drf_status.HTTP_409_CONFLICT,
            )

        if existing_report:
            existing_report.did = did
            existing_report.will_do = will_do
            existing_report.problems = problems
            existing_report.save(update_fields=["did", "will_do", "problems", "updated_at"])

            if existing_report.can_be_sent():
                existing_report.send()
                ReportsAuditService.log_report_submitted(request, existing_report)
            else:
                self._mark_rejected(existing_report)
                ReportsAuditService.log_report_rejected_empty(request, existing_report)

            return Response(
                {
                    "id": existing_report.id,
                    "status": existing_report.status,
                }
            )

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
            ReportsAuditService.log_report_submitted(request, report)
        else:
            self._mark_rejected(report)
            ReportsAuditService.log_report_rejected_empty(request, report)

        return Response(
            {
                "id": report.id,
                "status": report.status,
            },
            status=drf_status.HTTP_201_CREATED,
        )


class AdminOnboardingReportViewSet(ModelViewSet):
    queryset = OnboardingReport.objects.all()
    serializer_class = AdminOnboardingReportSerializer
    permission_classes = [IsAuthenticated, HasPermission]
    required_permission = "reports_review"
    http_method_names = ["get", "patch"]

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        old_status = instance.status

        new_status = request.data.get("status")
        comment = request.data.get("reviewer_comment")

        instance.set_status(
            new_status=new_status,
            reviewer=request.user,
            comment=comment,
        )
        ReportsAuditService.log_review_status_changed(
            request,
            report=instance,
            from_status=old_status,
            to_status=instance.status,
            has_comment=bool((comment or "").strip()),
        )

        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class OnboardingReportLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OnboardingReportLogSerializer
    permission_classes = [IsAuthenticated, HasPermission]
    required_permission = "logs_read"

    def get_queryset(self):
        return OnboardingReportLog.objects.select_related(
            "report", "author"
        )


class ReportNotificationViewSet(viewsets.ModelViewSet):
    serializer_class = ReportNotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ReportNotification.objects.filter(
            report__user=self.request.user
        )


class EmployeeDailyReportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not (AccessPolicy.is_employee(request.user) or AccessPolicy.is_admin(request.user) or AccessPolicy.is_super_admin(request.user)):
            return Response({"detail": "Access denied."}, status=drf_status.HTTP_403_FORBIDDEN)

        report_date = request.query_params.get("date")
        qs = EmployeeDailyReport.objects.select_related("user")
        if AccessPolicy.is_employee(request.user):
            qs = qs.filter(user=request.user)
        if report_date:
            qs = qs.filter(report_date=report_date)

        serializer = EmployeeDailyReportSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        if not AccessPolicy.is_employee(request.user):
            return Response({"detail": "Only employee can submit report."}, status=drf_status.HTTP_403_FORBIDDEN)

        report_date = request.data.get("report_date") or timezone.localdate()
        summary = (request.data.get("summary") or "").strip()
        if not summary:
            return Response({"detail": "summary is required"}, status=drf_status.HTTP_400_BAD_REQUEST)

        report, _ = EmployeeDailyReport.objects.update_or_create(
            user=request.user,
            report_date=report_date,
            defaults={"summary": summary},
        )
        return Response(EmployeeDailyReportSerializer(report).data, status=drf_status.HTTP_201_CREATED)
