from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import OnboardingReport
from .models import (
    OnboardingReport,
    OnboardingReportLog,
    ReportNotification,
)


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
        read_only_fields = [
            "status",
            "reviewer_comment",
            "created_at",
            "updated_at",
        ]

class OnboardingReportCreateSerializer(serializers.ModelSerializer):
    day_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = OnboardingReport
        fields = (
            "day_id",
            "did",
            "will_do",
            "problems",
        )

    def validate(self, data):
        if not data.get("did") or not data.get("will_do"):
            raise serializers.ValidationError(
                "Fields 'did' and 'will_do' are required"
            )
        return data

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
        read_only_fields = (
            "id",
            "created_at",
        )


class ReportNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportNotification
        fields = (
            "id",
            "report",
            "text",
            "created_at",
        )
        read_only_fields = (
            "id",
            "created_at",
        )

