from rest_framework import serializers
from .models import SystemLog


class SystemLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(
        source="actor.email",
        read_only=True,
    )

    class Meta:
        model = SystemLog
        fields = (
            "id",
            "actor_email",
            "action",
            "level",
            "metadata",
            "created_at",
        )
