from rest_framework import serializers
from django.utils import timezone
from urllib.parse import urlparse

from .models import (
    OnboardingDay,
    OnboardingMaterial,
    OnboardingProgress,
)

# =====================================================
# USER SERIALIZERS
# =====================================================

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
        )


class OnboardingDayDetailSerializer(serializers.ModelSerializer):
    materials = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

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
        )

    def _get_day_status(self, day, user):
        """
        DONE / IN_PROGRESS / LOCKED
        """
        progress = OnboardingProgress.objects.filter(
            user=user,
            day=day,
        ).first()

        if progress and progress.status == OnboardingProgress.Status.DONE:
            return "DONE"

        previous_day = (
            OnboardingDay.objects
            .filter(day_number__lt=day.day_number, is_active=True)
            .order_by("-day_number")
            .first()
        )

        if not previous_day:
            return "IN_PROGRESS"

        prev_done = OnboardingProgress.objects.filter(
            user=user,
            day=previous_day,
            status=OnboardingProgress.Status.DONE,
        ).exists()

        return "IN_PROGRESS" if prev_done else "LOCKED"

    def get_status(self, day):
        user = self.context["request"].user
        return self._get_day_status(day, user)

    def get_materials(self, day):
        user = self.context["request"].user
        status = self._get_day_status(day, user)

        if status == "LOCKED":
            return []

        materials = list(day.materials.all())

        # 🔥 ВАЖНО: сортировка по priority + position
        materials.sort(key=lambda m: (m.priority, m.position))

        return OnboardingMaterialSerializer(materials, many=True).data


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


# =====================================================
# ADMIN SERIALIZERS
# =====================================================

class AdminOnboardingMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnboardingMaterial
        fields = "__all__"

    def validate(self, attrs):
        """
        1. Максимум 10 материалов на день
        2. Валидация content по типу
        """
        day = attrs.get("day") or getattr(self.instance, "day", None)
        material_type = attrs.get("type") or getattr(self.instance, "type", None)
        content = attrs.get("content") or getattr(self.instance, "content", None)

        # ---------- лимит 10 ----------
        if day:
            qs = OnboardingMaterial.objects.filter(day=day)
            if self.instance:
                qs = qs.exclude(id=self.instance.id)

            if qs.count() >= 10:
                raise serializers.ValidationError(
                    "Maximum 10 materials are allowed per onboarding day."
                )

        # ---------- валидация content ----------
        if material_type and content:
            self._validate_content(material_type, content)

        return attrs

    def _validate_content(self, material_type: str, content: str):
        # TEXT — любой текст
        if material_type == OnboardingMaterial.MaterialType.TEXT:
            return

        # остальные — должны быть URL
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
            "materials",
        )

    def validate_deadline_time(self, value):
        """
        Проверяем только время (по ТЗ дедлайн — ЧЧ:ММ).
        """
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
