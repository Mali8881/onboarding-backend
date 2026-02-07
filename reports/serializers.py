from rest_framework import serializers
from django.utils import timezone

from .models import (
    OnboardingReport,
    OnboardingReportComment,
    OnboardingReportLog,
    ReportNotification,
)

# =====================================================
# USER SERIALIZERS
# =====================================================

class UserReportListSerializer(serializers.ModelSerializer):
    day_number = serializers.IntegerField(source="day.day_number", read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = OnboardingReport
        fields = (
            "id",
            "day_number",
            "status",
            "submitted_at",
            "created_at",
        )

    def get_status(self, report):
        # OVERDUE для черновика
        if report.status == OnboardingReport.Status.DRAFT:
            day = report.day
            if day.deadline_time:
                now = timezone.localtime()
                deadline = now.replace(
                    hour=day.deadline_time.hour,
                    minute=day.deadline_time.minute,
                    second=0,
                    microsecond=0,
                )
                if now > deadline:
                    return "OVERDUE"

        return report.status.upper()


class UserReportDetailSerializer(serializers.ModelSerializer):
    day_number = serializers.IntegerField(source="day.day_number", read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = OnboardingReport
        fields = (
            "id",
            "day_number",
            "did",
            "will_do",
            "problems",
            "attachment",
            "status",
            "submitted_at",
            "created_at",
            "updated_at",
        )

    def get_status(self, report):
        if report.status == OnboardingReport.Status.DRAFT:
            day = report.day
            if day.deadline_time:
                now = timezone.localtime()
                deadline = now.replace(
                    hour=day.deadline_time.hour,
                    minute=day.deadline_time.minute,
                    second=0,
                    microsecond=0,
                )
                if now > deadline:
                    return "OVERDUE"

        return report.status.upper()


class UserReportCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnboardingReport
        fields = (
            "day",
            "did",
            "will_do",
            "problems",
            "attachment",
        )

    def validate(self, attrs):
        instance = getattr(self, "instance", None)

        # ❌ нельзя редактировать после отправки
        if instance and instance.status != OnboardingReport.Status.DRAFT:
            raise serializers.ValidationError(
                "You cannot edit a report after submission."
            )

        return attrs

    def create(self, validated_data):
        user = self.context["request"].user

        return OnboardingReport.objects.create(
            user=user,
            status=OnboardingReport.Status.DRAFT,
            **validated_data,
        )


# =====================================================
# ADMIN SERIALIZERS
# =====================================================

class AdminReportListSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    day_number = serializers.IntegerField(source="day.day_number", read_only=True)

    class Meta:
        model = OnboardingReport
        fields = (
            "id",
            "user_email",
            "day_number",
            "status",
            "submitted_at",
            "created_at",
        )


class AdminReportDetailSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    day_number = serializers.IntegerField(source="day.day_number", read_only=True)
    comments = serializers.SerializerMethodField()

    class Meta:
        model = OnboardingReport
        fields = (
            "id",
            "user_email",
            "day_number",
            "did",
            "will_do",
            "problems",
            "attachment",
            "status",
            "submitted_at",
            "created_at",
            "updated_at",
            "comments",
        )

    def get_comments(self, report):
        return [
            {
                "author": c.author.email,
                "text": c.text,
                "created_at": c.created_at,
            }
            for c in report.comments.all().order_by("created_at")
        ]


class AdminReportStatusSerializer(serializers.Serializer):
    """
    approve / revision / reject
    """
    status = serializers.ChoiceField(
        choices=[
            OnboardingReport.Status.APPROVED,
            OnboardingReport.Status.REVISION,
            OnboardingReport.Status.REJECTED,
        ]
    )
    comment = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs["status"] == OnboardingReport.Status.REVISION and not attrs.get("comment"):
            raise serializers.ValidationError(
                {"comment": "Comment is required for revision status."}
            )
        return attrs


# =====================================================
# HISTORY & NOTIFICATIONS
# =====================================================

class ReportHistorySerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(
        source="actor.email",
        read_only=True,
    )

    class Meta:
        model = OnboardingReportLog
        fields = (
            "id",
            "action",
            "from_status",
            "to_status",
            "actor_email",
            "created_at",
        )


class ReportNotificationSerializer(serializers.ModelSerializer):
    report_id = serializers.UUIDField(source="report.id", read_only=True)

    class Meta:
        model = ReportNotification
        fields = (
            "id",
            "report_id",
            "type",
            "message",
            "is_read",
            "created_at",
        )
