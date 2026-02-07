from rest_framework import serializers
from .models import User, Department, Position


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ("id", "name")


class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ("id", "name")


class UserProfileSerializer(serializers.ModelSerializer):
    department = DepartmentSerializer(read_only=True)
    position = PositionSerializer(read_only=True)

    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.filter(is_active=True),
        source="department",
        write_only=True,
        required=False
    )

    position_id = serializers.PrimaryKeyRelatedField(
        queryset=Position.objects.filter(is_active=True),
        source="position",
        write_only=True,
        required=False
    )

    class Meta:
        model = User
        fields = (
            "id",
            "first_name",
            "last_name",
            "avatar",
            "department",
            "department_id",
            "position",
            "position_id",
            "custom_position",
            "telegram",
            "phone",
        )
