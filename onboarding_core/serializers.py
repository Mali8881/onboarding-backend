from rest_framework import serializers
from .models import OnboardingDay, OnboardingMaterial


class OnboardingMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnboardingMaterial
        fields = ("id", "type", "content", "position")


class OnboardingDayListSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnboardingDay
        fields = (
            "id",
            "day_number",
            "title",
            "description",
            "instructions",
            "deadline_time",
            "is_active",
            "position",
        )


class OnboardingDayDetailSerializer(serializers.ModelSerializer):
    materials = OnboardingMaterialSerializer(many=True, read_only=True)

    class Meta:
        model = OnboardingDay
        fields = (
            "id",
            "day_number",
            "title",
            "description",
            "instructions",
            "deadline_time",
            "is_active",
            "position",
            "materials",
        )
