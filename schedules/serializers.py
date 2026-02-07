from rest_framework import serializers
from .models import WorkSchedule
from accounts.models import User


class WorkScheduleListSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkSchedule
        fields = ("id", "name", "description")


class WorkScheduleDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkSchedule
        fields = ("id", "name", "description", "structure")


class ScheduleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "full_name")
