from urllib.parse import urlparse

from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from accounts.access_policy import AccessPolicy

from .models import OnboardingDay, OnboardingMaterial, OnboardingProgress
from apps.tasks.models import Task
from regulations.serializers import RegulationSerializer
from regulations.models import (
    Regulation,
    RegulationAcknowledgement,
    RegulationFeedback,
    RegulationKnowledgeCheck,
    RegulationReadProgress,
)


class OnboardingMaterialSerializer(serializers.ModelSerializer):
    priority = serializers.IntegerField(read_only=True)

    class Meta:
        model = OnboardingMaterial
        fields = (
            "id",
            "type",
            "content",
            "position",
            "priority",
        )


class OnboardingDayListSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnboardingDay
        fields = (
            "id",
            "day_number",
            "title",
            "goals",
            "description",
            "instructions",
            "deadline_time",
            "task_templates",
        )


class OnboardingDayDetailSerializer(serializers.ModelSerializer):
    materials = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    regulations = serializers.SerializerMethodField()
    tasks = serializers.SerializerMethodField()

    class Meta:
        model = OnboardingDay
        fields = (
            "id",
            "day_number",
            "title",
            "goals",
            "description",
            "instructions",
            "deadline_time",
            "status",
            "materials",
            "regulations",
            "tasks",
        )

    def _get_day_status(self, day, user):
        progress = OnboardingProgress.objects.filter(
            user=user,
            day=day,
        ).first()

        if progress and progress.status == OnboardingProgress.Status.DONE:
            return "DONE"

        return "IN_PROGRESS"

    @extend_schema_field(
        {
            "type": "string",
            "enum": ["DONE", "IN_PROGRESS"],
            "description": "Onboarding day status for current user",
        }
    )
    def get_status(self, day):
        user = self.context["request"].user
        return self._get_day_status(day, user)

    @extend_schema_field(
        {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "format": "uuid"},
                    "type": {
                        "type": "string",
                        "enum": ["TEXT", "LINK", "VIDEO", "FILE"],
                    },
                    "content": {"type": "string"},
                    "position": {"type": "integer"},
                    "priority": {"type": "integer"},
                },
            },
            "description": "Onboarding day materials",
        }
    )
    def get_materials(self, day):
        materials = list(day.materials.all())
        materials.sort(key=lambda m: (m.priority, m.position))
        return OnboardingMaterialSerializer(materials, many=True).data

    @extend_schema_field(
        {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "format": "uuid"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "type": {"type": "string", "enum": ["link", "file"]},
                    "content": {"type": "string"},
                    "action": {"type": "string", "enum": ["open", "download"]},
                    "is_mandatory_on_day_one": {"type": "boolean"},
                    "is_acknowledged": {"type": "boolean"},
                    "acknowledged_at": {"type": "string", "nullable": True},
                },
            },
            "description": "Regulations linked to this onboarding day",
        }
    )
    def get_regulations(self, day):
        user = self.context["request"].user
        if AccessPolicy.is_intern(user) and day.day_number == 1:
            regulations_qs = Regulation.objects.filter(is_active=True).order_by("position", "-created_at")
        else:
            regulations_qs = day.regulations.filter(is_active=True).order_by("position", "-created_at")
        ack_map = {
            ack.regulation_id: ack
            for ack in RegulationAcknowledgement.objects.filter(user=user, regulation__in=regulations_qs)
        }
        feedback_map = {
            regulation_id: True
            for regulation_id in RegulationFeedback.objects.filter(
                user=user,
                regulation__in=regulations_qs,
            ).values_list("regulation_id", flat=True)
        }
        knowledge_map = {
            regulation_id: True
            for regulation_id in RegulationKnowledgeCheck.objects.filter(
                user=user,
                regulation__in=regulations_qs,
                is_passed=True,
            ).values_list("regulation_id", flat=True)
        }
        read_progress = RegulationReadProgress.objects.filter(
            user=user,
            regulation__in=regulations_qs,
            is_read=True,
        )
        read_map = {item.regulation_id: True for item in read_progress}
        read_at_map = {item.regulation_id: item.read_at for item in read_progress}
        return RegulationSerializer(
            regulations_qs,
            many=True,
            context={
                "request": self.context["request"],
                "ack_map": ack_map,
                "feedback_map": feedback_map,
                "knowledge_map": knowledge_map,
                "read_map": read_map,
                "read_at_map": read_at_map,
            },
        ).data

    @extend_schema_field(
        {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "column": {"type": "string"},
                    "priority": {"type": "string"},
                    "due_date": {"type": "string", "nullable": True},
                },
            },
            "description": "Tasks linked to this onboarding day for current user",
        }
    )
    def get_tasks(self, day):
        user = self.context["request"].user
        tasks = Task.objects.filter(assignee=user, onboarding_day=day).select_related("column").order_by("-created_at")
        return [
            {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "column": task.column.name,
                "priority": task.priority,
                "due_date": task.due_date.isoformat() if task.due_date else None,
            }
            for task in tasks
        ]


class OnboardingProgressSerializer(serializers.ModelSerializer):
    day_id = serializers.UUIDField(source="day.id", read_only=True)
    day_number = serializers.IntegerField(source="day.day_number", read_only=True)
    title = serializers.CharField(source="day.title", read_only=True)

    class Meta:
        model = OnboardingProgress
        fields = (
            "id",
            "day_id",
            "day_number",
            "title",
            "status",
            "completed_at",
            "updated_at",
        )


class AdminOnboardingMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnboardingMaterial
        fields = "__all__"

    def validate(self, attrs):
        day = attrs.get("day") or getattr(self.instance, "day", None)
        material_type = attrs.get("type") or getattr(self.instance, "type", None)
        content = attrs.get("content") or getattr(self.instance, "content", None)

        if day:
            qs = OnboardingMaterial.objects.filter(day=day)
            if self.instance:
                qs = qs.exclude(id=self.instance.id)

            if qs.count() >= 10:
                raise serializers.ValidationError(
                    "Maximum 10 materials are allowed per onboarding day."
                )

        if material_type and content:
            self._validate_content(material_type, content)

        return attrs

    def _validate_content(self, material_type: str, content: str):
        if material_type == OnboardingMaterial.MaterialType.TEXT:
            return

        self._validate_url(content)

        if material_type == OnboardingMaterial.MaterialType.VIDEO:
            if not self._is_video_url(content):
                raise serializers.ValidationError(
                    "Video must be a YouTube or embedded video URL."
                )

    def _validate_url(self, value: str):
        parsed = urlparse(value)
        if not parsed.scheme or not parsed.netloc:
            raise serializers.ValidationError("Content must be a valid URL.")

    def _is_video_url(self, url: str) -> bool:
        return any(domain in url for domain in [
            "youtube.com",
            "youtu.be",
            "vimeo.com",
            "player.vimeo.com",
        ])


class AdminOnboardingDaySerializer(serializers.ModelSerializer):
    materials = AdminOnboardingMaterialSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = OnboardingDay
        fields = (
            "id",
            "day_number",
            "title",
            "goals",
            "description",
            "instructions",
            "deadline_time",
            "is_active",
            "position",
            "task_templates",
            "materials",
        )

    def validate_task_templates(self, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("task_templates must be a list.")
        normalized = []
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                raise serializers.ValidationError(f"task_templates[{index}] must be an object.")
            title = str(item.get("title", "")).strip()
            if not title:
                raise serializers.ValidationError(f"task_templates[{index}].title is required.")
            description = str(item.get("description", "")).strip()
            normalized.append({"title": title, "description": description})
        return normalized

    def validate_deadline_time(self, value):
        if value is None:
            return value

        now = timezone.localtime().time()

        if value < now:
            raise serializers.ValidationError(
                "Deadline time cannot be in the past."
            )

        return value


class AdminOnboardingProgressSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    day_number = serializers.IntegerField(source="day.day_number", read_only=True)
    day_title = serializers.CharField(source="day.title", read_only=True)

    class Meta:
        model = OnboardingProgress
        fields = (
            "id",
            "user_id",
            "username",
            "day_number",
            "day_title",
            "status",
            "completed_at",
            "created_at",
        )
