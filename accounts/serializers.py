from rest_framework import serializers
from .models import User, Role, Department, Position


# =========================
# USER SERIALIZER (READ)
# =========================

class UserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="role.name", read_only=True)
    role_level = serializers.IntegerField(source="role.level", read_only=True)
    department = serializers.CharField(source="department.name", read_only=True)
    position = serializers.CharField(source="position.name", read_only=True)
    manager = serializers.PrimaryKeyRelatedField(read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "role_level",
            "department",
            "position",
            "manager",
            "custom_position",
            "telegram",
            "phone",
            "photo",
        )

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()


# =========================
# LOGIN
# =========================

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class PasswordResetRequestSerializer(serializers.Serializer):
    username_or_email = serializers.CharField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    new_password = serializers.CharField(write_only=True)


# =========================
# ROLE
# =========================

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ("id", "name", "level")


# =========================
# DEPARTMENT
# =========================

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ("id", "name")


# =========================
# POSITION
# =========================

class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ("id", "name")


# =========================
# NOTIFICATION
# =========================


# =========================
# USER PROFILE UPDATE
# =========================

class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "photo",
            "department",
            "position",
            "custom_position",
            "telegram",
            "phone",
        )

    def validate(self, attrs):
        position = attrs.get("position")
        custom_position = attrs.get("custom_position")

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
