from rest_framework import serializers

from .models import WorkSchedule, UserWorkSchedule


class CalendarDaySerializer(serializers.Serializer):
    date = serializers.DateField()
    weekday = serializers.IntegerField()
    is_working_day = serializers.BooleanField()
    is_holiday = serializers.BooleanField()
    holiday_name = serializers.CharField(allow_blank=True)
    work_time = serializers.DictField(allow_null=True)
    break_time = serializers.DictField(allow_null=True)


class WorkScheduleSerializer(serializers.ModelSerializer):
    users_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = WorkSchedule
        fields = (
            "id",
            "name",
            "work_days",
            "start_time",
            "end_time",
            "break_start",
            "break_end",
            "is_default",
            "is_active",
            "users_count",
        )


class WorkScheduleSelectSerializer(serializers.Serializer):
    schedule_id = serializers.IntegerField()


class UserWorkScheduleSerializer(serializers.ModelSerializer):
    schedule_name = serializers.CharField(source="schedule.name", read_only=True)

    class Meta:
        model = UserWorkSchedule
        fields = ("id", "user", "schedule", "schedule_name", "approved", "requested_at")
        read_only_fields = ("id", "requested_at")


class ScheduleRequestDecisionSerializer(serializers.Serializer):
    approved = serializers.BooleanField()


class WorkScheduleMonthGenerateSerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=2000, max_value=2100)
    month = serializers.IntegerField(min_value=1, max_value=12)
    overwrite = serializers.BooleanField(required=False, default=False)
