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
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(),
        required=False,
        allow_null=True,
    )
    users_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Department
        fields = ("id", "name", "parent", "is_active", "users_count")

    def validate_parent(self, value):
        instance = getattr(self, "instance", None)
        if not instance or value is None:
            return value
        if value.id == instance.id:
            raise serializers.ValidationError("Отдел не может быть родителем сам себе.")

        # Simple cycle protection for parent chain.
        cursor = value
        while cursor is not None:
            if cursor.id == instance.id:
                raise serializers.ValidationError("Нельзя создать циклическую иерархию отделов.")
            cursor = cursor.parent
        return value


# =========================
# POSITION
# =========================

class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ("id", "name", "is_active")


class StructureUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    role = serializers.CharField(source="role.name", read_only=True)
    position = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "full_name",
            "role",
            "position",
            "username",
            "telegram",
            "phone",
        )

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username

    def get_position(self, obj):
        if obj.position_id:
            return obj.position.name
        return obj.custom_position or ""


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
