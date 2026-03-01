from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import (
    EmployeeDailyReport,
    OnboardingReport,
    OnboardingReportLog,
    ReportNotification,
)


# =====================================================
# USER SERIALIZER
# =====================================================

class OnboardingReportSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(
        source="user.email",
        read_only=True
    )
    day_number = serializers.IntegerField(
        source="day.day_number",
        read_only=True
    )

    class Meta:
        model = OnboardingReport
        fields = [
            "id",
            "user",
            "user_email",
            "day",
            "day_number",
            "did",
            "will_do",
            "problems",
            "status",
            "reviewer_comment",
            "created_at",
            "updated_at",
        ]
        read_only_fields = (
            "status",
            "reviewer_comment",
            "created_at",
            "updated_at",
        )


# =====================================================
# CREATE SERIALIZER
# =====================================================

class OnboardingReportCreateSerializer(serializers.Serializer):
    day_id = serializers.UUIDField()
    did = serializers.CharField(allow_blank=True)
    will_do = serializers.CharField(allow_blank=True)
    problems = serializers.CharField(allow_blank=True, required=False)

    def validate(self, data):
        # НИЧЕГО не запрещаем.
        # Логика пустого отчёта обрабатывается в модели.
        return data


# =====================================================
# ADMIN SERIALIZER
# =====================================================

class AdminOnboardingReportSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    day = serializers.SerializerMethodField()

    class Meta:
        model = OnboardingReport
        fields = (
            "id",
            "user",
            "day",
            "status",
            "reviewer_comment",
            "created_at",
        )
        read_only_fields = (
            "created_at",
        )

    @extend_schema_field(
        {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "username": {"type": "string"},
            },
        }
    )
    def get_user(self, obj):
        return {
            "id": obj.user.id,
            "username": obj.user.username,
        }

    @extend_schema_field(
        {
            "type": "object",
            "properties": {
                "id": {"type": "string", "format": "uuid"},
                "day_number": {"type": "integer"},
                "title": {"type": "string"},
            },
        }
    )
    def get_day(self, obj):
        return {
            "id": str(obj.day.id),
            "day_number": obj.day.day_number,
            "title": obj.day.title,
        }

    def validate(self, attrs):
        new_status = attrs.get("status")

        if new_status in [OnboardingReport.Status.REVISION, OnboardingReport.Status.REJECTED]:
            if not attrs.get("reviewer_comment"):
                raise serializers.ValidationError(
                    {"reviewer_comment": "Комментарий обязателен"}
                )

        return attrs


# =====================================================
# LOG SERIALIZER
# =====================================================

class OnboardingReportLogSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(
        source="author.username",
        read_only=True
    )

    class Meta:
        model = OnboardingReportLog
        fields = (
            "id",
            "report",
            "action",
            "author",
            "author_username",
            "created_at",
        )



# =====================================================
# NOTIFICATION SERIALIZER
# =====================================================

class ReportNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportNotification
        fields = (
            "id",
            "report",
            "text",
            "created_at",
        )


class EmployeeDailyReportSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    user_full_name = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeDailyReport
        fields = (
            "id",
            "user",
            "username",
            "user_full_name",
            "report_date",
            "summary",
            "started_tasks",
            "taken_tasks",
            "completed_tasks",
            "blockers",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("user", "username", "created_at", "updated_at")

    def get_user_full_name(self, obj):
        full_name = f"{obj.user.first_name} {obj.user.last_name}".strip()
        return full_name or obj.user.username
