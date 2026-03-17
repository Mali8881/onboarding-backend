from rest_framework import serializers

from common.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = (
            "id",
            "title",
            "message",
            "type",
            "event_key",
            "is_pinned",
            "is_read",
            "expires_at",
            "created_at",
        )
