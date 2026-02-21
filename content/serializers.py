from rest_framework import serializers
# Импортируем все модели из одного места
from .models import (
    News, WelcomeBlock, Feedback, Employee,
    Instruction, LanguageSetting, NewsSliderSettings, Course, CourseEnrollment
)
from accounts.models import User

# 1. СЕРИАЛИЗАТОРЫ ДЛЯ НОВОСТЕЙ
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
        # Вызываем метод из модели, если он там есть
        return obj.get_short_text() if hasattr(obj, 'get_short_text') else ""

class NewsListSerializer(serializers.ModelSerializer):
    """Специальный легкий сериализатор для списка (без тяжелого поля full_text)"""
    short_text = serializers.SerializerMethodField()

    class Meta:
        model = News
        fields = ("id", "title", "short_text", "image", "published_at")

    def get_short_text(self, obj):
        return obj.get_short_text() if hasattr(obj, 'get_short_text') else ""

class NewsDetailSerializer(serializers.ModelSerializer):
    """Сериализатор для полной новости"""
    class Meta:
        model = News
        fields = ("id", "title", "full_text", "image", "published_at")


# 2. ПРИВЕТСТВЕННЫЙ БЛОК
class WelcomeBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = WelcomeBlock
        fields = "__all__"


# 3. ОБРАТНАЯ СВЯЗЬ
from rest_framework import serializers


class FeedbackSerializer(serializers.ModelSerializer):

    class Meta:
        model = Feedback
        fields = '__all__'
        read_only_fields = ('created_at',)

    def validate_text(self, value):
        if not value.strip():
            raise serializers.ValidationError("Текст не может быть пустым")
        return value

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


# 4. СОТРУДНИКИ
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


# 5. ИНСТРУКЦИИ
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
            # Возвращает полный URL файла (удобно для фронта)
            return obj.file.url
        return None


# 6. ЯЗЫКИ
class LanguageSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = LanguageSetting
        fields = ("code", "is_enabled")


# 7. НАСТРОЙКИ СЛАЙДЕРА
class NewsSliderSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsSliderSettings
        fields = ['autoplay', 'autoplay_delay']


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


