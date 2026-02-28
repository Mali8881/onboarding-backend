from django.utils import timezone
from rest_framework import serializers

from .models import (
    InternOnboardingRequest,
    Regulation,
    RegulationAcknowledgement,
    RegulationFeedback,
    RegulationReadReport,
    RegulationQuiz,
    RegulationQuizAttempt,
    RegulationQuizOption,
    RegulationQuizQuestion,
    RegulationReadProgress,
)


class RegulationSerializer(serializers.ModelSerializer):
    content = serializers.SerializerMethodField()
    action = serializers.SerializerMethodField()
    is_acknowledged = serializers.SerializerMethodField()
    acknowledged_at = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    quiz_required = serializers.SerializerMethodField()
    quiz_passed = serializers.SerializerMethodField()
    report_required_today = serializers.SerializerMethodField()
    report_submitted_today = serializers.SerializerMethodField()

    class Meta:
        model = Regulation
        fields = (
            "id",
            "title",
            "description",
            "type",
            "content",
            "action",
            "is_mandatory_on_day_one",
            "read_deadline_at",
            "is_overdue",
            "quiz_required",
            "quiz_passed",
            "report_required_today",
            "report_submitted_today",
            "is_acknowledged",
            "acknowledged_at",
            "position",
        )

    def get_content(self, obj):
        if obj.type == Regulation.RegulationType.LINK:
            return obj.external_url
        if obj.type == Regulation.RegulationType.FILE and obj.file:
            return obj.file.url
        return None

    def get_action(self, obj):
        # File can also be opened by URL in browser; keep action unified for frontend.
        return "open"

    def _ack(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None

        ack_map = self.context.get("ack_map")
        if ack_map is not None:
            return ack_map.get(obj.id)

        return RegulationAcknowledgement.objects.filter(
            user=request.user,
            regulation=obj,
        ).first()

    def get_is_acknowledged(self, obj):
        return self._ack(obj) is not None

    def get_acknowledged_at(self, obj):
        ack = self._ack(obj)
        return ack.acknowledged_at if ack else None

    def get_is_overdue(self, obj):
        if not obj.read_deadline_at:
            return False
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False

        progress_map = self.context.get("read_progress_map") or {}
        progress = progress_map.get(obj.id)
        if progress and progress.is_read:
            return False
        return timezone.now() > obj.read_deadline_at

    def get_quiz_required(self, obj):
        quiz_required_map = self.context.get("quiz_required_map")
        if quiz_required_map is not None:
            return bool(quiz_required_map.get(obj.id, False))
        return RegulationQuiz.objects.filter(regulation=obj, is_active=True).exists()

    def get_quiz_passed(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        quiz_passed_map = self.context.get("quiz_passed_map") or {}
        return bool(quiz_passed_map.get(obj.id, False))

    def get_report_required_today(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        progress_map = self.context.get("read_progress_map") or {}
        progress = progress_map.get(obj.id)
        if not progress or not progress.is_read or not progress.read_at:
            return False
        return progress.read_at.date() == timezone.localdate()

    def get_report_submitted_today(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        report_map = self.context.get("read_report_map") or {}
        return bool(report_map.get(obj.id, False))


class RegulationAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Regulation
        fields = (
            "id",
            "title",
            "description",
            "type",
            "external_url",
            "file",
            "position",
            "is_active",
            "is_mandatory_on_day_one",
            "read_deadline_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        reg_type = attrs.get("type", getattr(self.instance, "type", None))
        external_url = attrs.get("external_url", getattr(self.instance, "external_url", None))
        file = attrs.get("file", getattr(self.instance, "file", None))

        if reg_type == Regulation.RegulationType.LINK:
            if not external_url:
                raise serializers.ValidationError(
                    {"external_url": "Для типа 'link' ссылка обязательна."}
                )
            attrs["file"] = None

        if reg_type == Regulation.RegulationType.FILE:
            if not file:
                raise serializers.ValidationError(
                    {"file": "Для типа 'file' файл обязателен."}
                )
            attrs["external_url"] = None

        return attrs


class RegulationAcknowledgementSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegulationAcknowledgement
        fields = (
            "id",
            "user",
            "regulation",
            "acknowledged_at",
            "user_full_name",
            "regulation_title",
        )
        read_only_fields = fields


class RegulationReadProgressSerializer(serializers.ModelSerializer):
    regulation = RegulationSerializer(read_only=True)

    class Meta:
        model = RegulationReadProgress
        fields = ("regulation", "is_read", "read_at")


class RegulationFeedbackCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegulationFeedback
        fields = ("text",)


class RegulationReadReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegulationReadReport
        fields = ("report_text",)


class RegulationQuizOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegulationQuizOption
        fields = ("id", "text", "position")


class RegulationQuizQuestionSerializer(serializers.ModelSerializer):
    options = RegulationQuizOptionSerializer(many=True, read_only=True)

    class Meta:
        model = RegulationQuizQuestion
        fields = ("id", "text", "position", "options")


class RegulationQuizSerializer(serializers.ModelSerializer):
    questions = RegulationQuizQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = RegulationQuiz
        fields = ("id", "regulation", "title", "description", "passing_score", "questions")
        read_only_fields = fields


class RegulationQuizSubmitSerializer(serializers.Serializer):
    answers = serializers.DictField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
        help_text="Mapping question_id -> selected option_id",
    )


class RegulationQuizResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegulationQuizAttempt
        fields = ("score_percent", "passed", "submitted_at")


class InternOnboardingRequestSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = InternOnboardingRequest
        fields = (
            "id",
            "user",
            "username",
            "status",
            "note",
            "requested_at",
            "reviewed_at",
            "reviewed_by",
        )
        read_only_fields = ("requested_at", "reviewed_at", "reviewed_by")
