from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Count

from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.viewsets import ModelViewSet

from common.permissions import IsAdminOrSuperAdmin
from onboarding_core.models import OnboardingProgress

from security.models import SystemLog

from .models import (
    OnboardingReport,
    OnboardingReportComment,
    OnboardingReportLog,
    ReportNotification,
)

from .serializers import (
    UserReportListSerializer,
    UserReportDetailSerializer,
    UserReportCreateUpdateSerializer,
    AdminReportListSerializer,
    AdminReportStatusSerializer,
    ReportHistorySerializer,
    ReportNotificationSerializer,
)

# =====================================================
# USER API
# =====================================================

class MyReportListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserReportListSerializer

    def get_queryset(self):
        return (
            OnboardingReport.objects
            .filter(user=self.request.user)
            .select_related("day")
            .order_by("-created_at")
        )


class MyReportDetailView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserReportDetailSerializer
    lookup_field = "id"

    def get_queryset(self):
        return (
            OnboardingReport.objects
            .filter(user=self.request.user)
            .select_related("day")
        )


class MyReportCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UserReportCreateUpdateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        report = serializer.save()

        OnboardingReportLog.objects.create(
            report=report,
            actor=request.user,
            action=OnboardingReportLog.Action.CREATED,
            to_status=report.status,
        )

        return Response(
            UserReportDetailSerializer(report).data,
            status=status.HTTP_201_CREATED,
        )


class SubmitReportView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        report = get_object_or_404(
            OnboardingReport,
            id=id,
            user=request.user,
        )

        if report.status != OnboardingReport.Status.DRAFT:
            return Response(
                {"detail": "Report cannot be submitted"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ⏰ дедлайн
        if report.day.deadline_time:
            now = timezone.localtime()
            deadline = now.replace(
                hour=report.day.deadline_time.hour,
                minute=report.day.deadline_time.minute,
                second=0,
                microsecond=0,
            )

            if now > deadline:
                report.status = OnboardingReport.Status.REJECTED
                report.submitted_at = timezone.now()
                report.save()

                ReportNotification.objects.create(
                    user=request.user,
                    report=report,
                    message="Отчёт отклонён: дедлайн истёк ⏰",
                )

                return Response(
                    {"detail": "Deadline has passed"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # ❌ пустой отчёт
        if not report.did and not report.will_do and not report.problems:
            report.status = OnboardingReport.Status.REJECTED
            report.submitted_at = timezone.now()
            report.save()

            ReportNotification.objects.create(
                user=request.user,
                report=report,
                message="Пустой отчёт отклонён ❌",
            )

            return Response(
                {"detail": "Empty report rejected"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        report.status = OnboardingReport.Status.SUBMITTED
        report.submitted_at = timezone.now()
        report.save()

        ReportNotification.objects.create(
            user=request.user,
            report=report,
            message=f"Отчёт за день {report.day.day_number} отправлен",
        )

        OnboardingReportLog.objects.create(
            report=report,
            actor=request.user,
            action=OnboardingReportLog.Action.SUBMITTED,
            from_status=OnboardingReport.Status.DRAFT,
            to_status=report.status,
        )

        return Response(
            {"detail": "Report submitted"},
            status=status.HTTP_200_OK,
        )


class MyReportNotificationsView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReportNotificationSerializer

    def get_queryset(self):
        return (
            ReportNotification.objects
            .filter(user=self.request.user)
            .order_by("-created_at")
        )


class MarkNotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        notification = get_object_or_404(
            ReportNotification,
            id=id,
            user=request.user,
        )

        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read"])

        return Response(
            {"detail": "Notification marked as read"},
            status=status.HTTP_200_OK,
        )


class MyUnreadNotificationsCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = ReportNotification.objects.filter(
            user=request.user,
            is_read=False,
        ).count()

        return Response({"unread": count})


class ReportHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        report = get_object_or_404(OnboardingReport, id=id)

        if request.user.role == "INTERN" and report.user != request.user:
            return Response(
                {"detail": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN,
            )

        logs = report.logs.select_related("actor").order_by("created_at")
        serializer = ReportHistorySerializer(logs, many=True)
        return Response(serializer.data)


# =====================================================
# ADMIN API
# =====================================================

class AdminReportViewSet(ModelViewSet):
    permission_classes = [IsAdminOrSuperAdmin]
    serializer_class = AdminReportListSerializer
    http_method_names = ["get"]

    def get_queryset(self):
        qs = OnboardingReport.objects.select_related("user", "day")

        user_id = self.request.query_params.get("user_id")
        status_param = self.request.query_params.get("status")
        day_number = self.request.query_params.get("day_number")

        if user_id:
            qs = qs.filter(user_id=user_id)
        if status_param:
            qs = qs.filter(status=status_param)
        if day_number:
            qs = qs.filter(day__day_number=day_number)

        return qs.order_by("-created_at")


class AdminReportStatusView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    def post(self, request, id):
        report = get_object_or_404(OnboardingReport, id=id)

        serializer = AdminReportStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data["status"]
        comment = serializer.validated_data.get("comment")

        old_status = report.status
        report.status = new_status
        report.save()

        # 🔐 SYSTEM LOG
        SystemLog.objects.create(
            actor=request.user,
            action="REPORT_STATUS_CHANGED",
            level=SystemLog.Level.INFO,
            metadata={
                "report_id": str(report.id),
                "old_status": old_status,
                "new_status": new_status,
            },
        )

        if comment:
            OnboardingReportComment.objects.create(
                report=report,
                author=request.user,
                text=comment,
            )

        if new_status == OnboardingReport.Status.APPROVED:
            progress, _ = OnboardingProgress.objects.get_or_create(
                user=report.user,
                day=report.day,
            )
            progress.mark_done()
            progress.save()

        ReportNotification.objects.create(
            user=report.user,
            report=report,
            message=f"Статус отчёта изменён: {new_status}",
        )

        OnboardingReportLog.objects.create(
            report=report,
            actor=request.user,
            action=new_status,
            from_status=old_status,
            to_status=new_status,
        )

        return Response(
            {"detail": "Status updated"},
            status=status.HTTP_200_OK,
        )


class OnboardingStatsView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    def get(self, request):
        return Response({
            "total_reports": OnboardingReport.objects.count(),
            "by_status": (
                OnboardingReport.objects
                .values("status")
                .annotate(count=Count("id"))
            )
        })
