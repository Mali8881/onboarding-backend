from rest_framework import serializers
from .models import User


# =====================================================
# USER
# =====================================================

class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "role",
            "is_blocked",
            "full_name",
            "telegram",
            "phone",
        )


# =====================================================
# ADMIN
# =====================================================

class AdminUserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "role",
            "is_blocked",
            "full_name",
            "telegram",
            "phone",
        )


class AdminUserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "password",
            "role",
            "full_name",
        )

    def validate_role(self, value):
        request = self.context["request"]

        # ❌ ADMIN может создавать только INTERN
        if request.user.role == "ADMIN" and value != "INTERN":
            raise serializers.ValidationError(
                "ADMIN can create only INTERN users"
            )

        # ❌ INTERN вообще не имеет доступа
        if request.user.role == "INTERN":
            raise serializers.ValidationError("Permission denied")

        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
