from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Board, Column, Task


User = get_user_model()


class TaskSerializer(serializers.ModelSerializer):
    assignee_username = serializers.CharField(source="assignee.username", read_only=True)
    reporter_username = serializers.CharField(source="reporter.username", read_only=True)

    class Meta:
        model = Task
        fields = (
            "id",
            "board",
            "column",
            "title",
            "description",
            "assignee",
            "assignee_username",
            "reporter",
            "reporter_username",
            "due_date",
            "priority",
            "onboarding_day",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("reporter", "created_at", "updated_at")


class TaskCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    assignee_id = serializers.IntegerField()
    onboarding_day_id = serializers.UUIDField(required=False, allow_null=True)
    due_date = serializers.DateField(required=False, allow_null=True)
    priority = serializers.ChoiceField(choices=Task.Priority.choices, default=Task.Priority.MEDIUM)

    def validate_assignee_id(self, value):
        user = User.objects.filter(id=value).first()
        if not user:
            raise serializers.ValidationError("Assignee not found.")
        return value


class TaskMoveSerializer(serializers.Serializer):
    column_id = serializers.IntegerField()

    def validate_column_id(self, value):
        if not Column.objects.filter(id=value).exists():
            raise serializers.ValidationError("Column not found.")
        return value

