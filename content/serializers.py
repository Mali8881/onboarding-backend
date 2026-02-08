from rest_framework import serializers
# Импортируем все модели из одного места
from .models import (
    News, WelcomeBlock, Feedback, Employee,
    Instruction, LanguageSetting, NewsSliderSettings
)

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