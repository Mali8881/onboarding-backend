from datetime import date

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import AttendanceMark, WorkCalendarDay
from .policies import AttendancePolicy


User = get_user_model()


class MonthQuerySerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=2000, max_value=2100)
    month = serializers.IntegerField(min_value=1, max_value=12)


class AttendanceTeamFilterSerializer(MonthQuerySerializer):
    user_id = serializers.IntegerField(required=False)
    position_id = serializers.IntegerField(required=False)
    status = serializers.ChoiceField(
        choices=AttendanceMark.Status.choices,
        required=False,
    )


class WorkCalendarGenerateSerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=2000, max_value=2100)
    month = serializers.IntegerField(min_value=1, max_value=12)
    overwrite = serializers.BooleanField(required=False, default=False)


class AttendanceMarkSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = AttendanceMark
        fields = (
            "id",
            "user",
            "username",
            "date",
            "status",
            "comment",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_by", "created_at", "updated_at")


class AttendanceMarkUpsertSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=False)
    date = serializers.DateField()
    status = serializers.ChoiceField(choices=AttendanceMark.Status.choices)
    comment = serializers.CharField(required=False, allow_blank=True)

    def validate_date(self, value):
        if value > date.today():
            raise serializers.ValidationError("Future dates are not allowed.")
        return value

    def validate(self, attrs):
        request = self.context["request"]
        user_id = attrs.get("user_id")
        target_user = request.user
        if user_id is not None:
            target_user = User.objects.filter(id=user_id).first()
            if not target_user:
                raise serializers.ValidationError({"user_id": "User not found."})

        if not AttendancePolicy.can_edit_mark(request.user, target_user, attrs["date"]):
            raise serializers.ValidationError({"detail": "Access denied."})

        attrs["target_user"] = target_user
        return attrs


class WorkCalendarDaySerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkCalendarDay
        fields = ("date", "is_working_day", "is_holiday", "note")


class WorkCalendarDayUpsertSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkCalendarDay
        fields = ("date", "is_working_day", "is_holiday", "note")
