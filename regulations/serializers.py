from rest_framework import serializers

from .models import (
    InternOnboardingRequest,
    Regulation,
    RegulationAcknowledgement,
    RegulationFeedback,
    RegulationKnowledgeCheck,
    RegulationReadProgress,
)


class RegulationSerializer(serializers.ModelSerializer):
    content = serializers.SerializerMethodField()
    action = serializers.SerializerMethodField()
    is_acknowledged = serializers.SerializerMethodField()
    acknowledged_at = serializers.SerializerMethodField()
    has_feedback = serializers.SerializerMethodField()
    has_passed_quiz = serializers.SerializerMethodField()
    is_read = serializers.SerializerMethodField()
    read_at = serializers.SerializerMethodField()

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
            "is_acknowledged",
            "acknowledged_at",
            "position",
            "quiz_question",
            "has_feedback",
            "has_passed_quiz",
            "is_read",
            "read_at",
        )

    def get_content(self, obj):
        if obj.type == Regulation.RegulationType.LINK:
            return obj.external_url
        if obj.type == Regulation.RegulationType.FILE and obj.file:
            return obj.file.url
        return None

    def get_action(self, obj):
        if obj.type == Regulation.RegulationType.LINK:
            return "open"
        return "download"

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

    def get_has_feedback(self, obj):
        feedback_map = self.context.get("feedback_map")
        if feedback_map is not None:
            return bool(feedback_map.get(obj.id))

        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return RegulationFeedback.objects.filter(user=request.user, regulation=obj).exists()

    def get_has_passed_quiz(self, obj):
        knowledge_map = self.context.get("knowledge_map")
        if knowledge_map is not None:
            return bool(knowledge_map.get(obj.id))

        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return RegulationKnowledgeCheck.objects.filter(
            user=request.user,
            regulation=obj,
            is_passed=True,
        ).exists()

    def get_is_read(self, obj):
        read_map = self.context.get("read_map")
        if read_map is not None:
            return bool(read_map.get(obj.id))

        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return RegulationReadProgress.objects.filter(
            user=request.user,
            regulation=obj,
            is_read=True,
        ).exists()

    def get_read_at(self, obj):
        read_at_map = self.context.get("read_at_map")
        if read_at_map is not None:
            return read_at_map.get(obj.id)

        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        progress = RegulationReadProgress.objects.filter(
            user=request.user,
            regulation=obj,
        ).first()
        return progress.read_at if progress and progress.is_read else None


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
            "language",
            "quiz_question",
            "quiz_expected_answer",
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
                    {"external_url": "For type 'link' external_url is required."}
                )
            attrs["file"] = None

        if reg_type == Regulation.RegulationType.FILE:
            if not file:
                raise serializers.ValidationError(
                    {"file": "For type 'file' file is required."}
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


class RegulationQuizSubmitSerializer(serializers.Serializer):
    answer = serializers.CharField(allow_blank=False, trim_whitespace=True)


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
