from rest_framework import serializers
from .models import User, Department, Position


class DepartmentSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(
        read_only=True,
        help_text="Уникальный идентификатор подразделения."
    )

    name = serializers.CharField(
        read_only=True,
        help_text=(
            "Название подразделения компании. "
            "Используется для отображения в списках и выпадающих селектах."
        )
    )

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

    def validate(self, attrs):
        position = attrs.get("position")
        custom_position = attrs.get("custom_position")

        # если PATCH — учитываем текущие значения
        if self.instance:
            position = position if "position" in attrs else self.instance.position
            custom_position = (
                custom_position
                if "custom_position" in attrs
                else self.instance.custom_position
            )

        if position and custom_position:
            raise serializers.ValidationError(
                "Укажите либо должность из списка, либо другую должность, но не оба поля."
            )

        if not position and not custom_position:
            raise serializers.ValidationError(
                "Необходимо указать должность из списка или другую должность."
            )

        return attrs
