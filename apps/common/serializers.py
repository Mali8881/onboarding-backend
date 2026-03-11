from rest_framework import serializers
from apps.common.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = (
            "id",
            "title",
            "message",
            "type",
            "code",
            "severity",
            "entity_type",
            "entity_id",
            "action_url",
            "is_read",
            "created_at",
        )
