from rest_framework import serializers

from accounts.models import User
from .models import (
    Course,
    CourseEnrollment,
    Employee,
    Feedback,
    Instruction,
    LanguageSetting,
    News,
    NewsSliderSettings,
    WelcomeBlock,
)


class NewsSerializer(serializers.ModelSerializer):
    short_text = serializers.SerializerMethodField()

    class Meta:
        model = News
        fields = (
            "id",
            "title",
            "short_text",
            "full_text",
            "image",
            "published_at",
        )

    def get_short_text(self, obj):
        return obj.get_short_text() if hasattr(obj, "get_short_text") else ""


class NewsListSerializer(serializers.ModelSerializer):
    short_text = serializers.SerializerMethodField()

    class Meta:
        model = News
        fields = ("id", "title", "short_text", "image", "published_at")

    def get_short_text(self, obj):
        return obj.get_short_text() if hasattr(obj, "get_short_text") else ""


class NewsDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = News
        fields = ("id", "title", "full_text", "image", "published_at")


class WelcomeBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = WelcomeBlock
        fields = "__all__"


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = "__all__"
        read_only_fields = ("created_at",)

    def validate_text(self, value):
        if not value.strip():
            raise serializers.ValidationError("Text must not be empty")
        return value


class FeedbackAdminListSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source="get_type_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    employee = serializers.SerializerMethodField()
    short_text = serializers.SerializerMethodField()

    class Meta:
        model = Feedback
        fields = (
            "id",
            "type",
            "type_label",
            "status",
            "status_label",
            "is_read",
            "is_anonymous",
            "full_name",
            "contact",
            "employee",
            "text",
            "short_text",
            "created_at",
        )

    def get_employee(self, obj):
        if obj.is_anonymous:
            return "Анонимно"
        return obj.full_name or "Без имени"

    def get_short_text(self, obj):
        text = (obj.text or "").strip()
        return text if len(text) <= 90 else f"{text[:87]}..."


class FeedbackCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = (
            "type",
            "text",
            "full_name",
            "contact",
        )


class FeedbackResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = (
            "id",
            "type",
            "text",
            "full_name",
            "contact",
            "is_read",
            "created_at",
        )


class FeedbackStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Feedback.STATUS_CHOICES)


class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = (
            "id",
            "full_name",
            "position",
            "department",
            "telegram",
            "photo",
        )


class InstructionSerializer(serializers.ModelSerializer):
    content = serializers.SerializerMethodField()

    class Meta:
        model = Instruction
        fields = (
            "id",
            "language",
            "type",
            "content",
            "updated_at",
        )

    def get_content(self, obj):
        if obj.type == "text":
            return obj.text
        if obj.type == "link":
            return obj.external_url
        if obj.type == "file" and obj.file:
            return obj.file.url
        return None


class LanguageSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = LanguageSetting
        fields = ("code", "is_enabled")


class NewsSliderSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsSliderSettings
        fields = ["autoplay", "autoplay_delay"]


class CourseSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = Course
        fields = (
            "id",
            "title",
            "description",
            "visibility",
            "department",
            "department_name",
            "is_active",
        )


class CourseEnrollmentSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)

    class Meta:
        model = CourseEnrollment
        fields = (
            "id",
            "course",
            "source",
            "status",
            "progress_percent",
            "accepted_at",
            "started_at",
            "completed_at",
            "updated_at",
        )


class CourseAssignSerializer(serializers.Serializer):
    course_id = serializers.UUIDField()
    user_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=False,
    )
    assign_to_all = serializers.BooleanField(default=False)

    def validate(self, attrs):
        course_id = attrs["course_id"]
        user_ids = attrs.get("user_ids")
        assign_to_all = attrs.get("assign_to_all", False)

        try:
            course = Course.objects.get(id=course_id, is_active=True)
        except Course.DoesNotExist as exc:
            raise serializers.ValidationError({"course_id": "Course not found."}) from exc

        if not assign_to_all and not user_ids:
            raise serializers.ValidationError("Provide user_ids or set assign_to_all=true.")

        attrs["course"] = course
        return attrs


class CourseAcceptSerializer(serializers.Serializer):
    enrollment_id = serializers.UUIDField()


class CourseProgressUpdateSerializer(serializers.Serializer):
    enrollment_id = serializers.UUIDField()
    progress_percent = serializers.IntegerField(min_value=0, max_value=100)


class CourseSelfEnrollSerializer(serializers.Serializer):
    course_id = serializers.UUIDField()


class CourseUserShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username")
