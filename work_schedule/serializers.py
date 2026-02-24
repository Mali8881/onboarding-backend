from datetime import datetime
from datetime import timedelta

from rest_framework import serializers

from .models import WeeklyWorkPlan, WorkSchedule, UserWorkSchedule


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


class WeeklyWorkPlanUpsertSerializer(serializers.Serializer):
    class ShiftSerializer(serializers.Serializer):
        date = serializers.DateField()
        start_time = serializers.TimeField(format="%H:%M", input_formats=["%H:%M"], required=False, allow_null=True)
        end_time = serializers.TimeField(format="%H:%M", input_formats=["%H:%M"], required=False, allow_null=True)
        mode = serializers.ChoiceField(choices=("office", "online", "day_off"))
        comment = serializers.CharField(required=False, allow_blank=True)

    week_start = serializers.DateField()
    days = ShiftSerializer(many=True)
    online_reason = serializers.CharField(required=False, allow_blank=True)
    employee_comment = serializers.CharField(required=False, allow_blank=True)

    def validate_week_start(self, value):
        if value.weekday() != 0:
            raise serializers.ValidationError("week_start must be a Monday.")
        return value

    def validate(self, attrs):
        days = attrs["days"]
        if len(days) != 7:
            raise serializers.ValidationError({"days": "Exactly 7 shifts are required (Monday..Sunday)."})

        week_start = attrs["week_start"]
        week_end = week_start + timedelta(days=6)
        expected_dates = {week_start + timedelta(days=i) for i in range(7)}
        seen_dates = set()

        total_office = 0
        total_online = 0
        normalized_days = []
        for idx, item in enumerate(days, start=1):
            day_date = item["date"]
            if day_date < week_start or day_date > week_end:
                raise serializers.ValidationError({"days": f"Shift #{idx}: date must be inside selected week."})
            if day_date not in expected_dates:
                raise serializers.ValidationError({"days": f"Shift #{idx}: date must be inside Monday..Sunday."})
            if day_date in seen_dates:
                raise serializers.ValidationError({"days": f"Shift #{idx}: duplicate date {day_date.isoformat()}."})
            seen_dates.add(day_date)

            mode = item["mode"]
            start_time = item.get("start_time")
            end_time = item.get("end_time")

            if mode == "day_off":
                if start_time is not None or end_time is not None:
                    raise serializers.ValidationError({"days": f"Shift #{idx}: day_off must not contain start/end time."})
                normalized_days.append(
                    {
                        "date": day_date.isoformat(),
                        "start_time": None,
                        "end_time": None,
                        "mode": mode,
                        "comment": item.get("comment", ""),
                    }
                )
                continue

            if start_time is None or end_time is None:
                raise serializers.ValidationError({"days": f"Shift #{idx}: start_time and end_time are required."})
            if start_time.minute != 0 or end_time.minute != 0:
                raise serializers.ValidationError({"days": f"Shift #{idx}: use full hours only (HH:00)."})

            start_dt = datetime.combine(day_date, start_time)
            end_dt = datetime.combine(day_date, end_time)
            if end_dt <= start_dt:
                raise serializers.ValidationError({"days": f"Shift #{idx}: end_time must be after start_time."})

            min_hour, max_hour = self._day_hour_limits(day_date)
            if start_time.hour < min_hour or end_time.hour > max_hour:
                raise serializers.ValidationError(
                    {"days": f"Shift #{idx}: allowed time is {min_hour:02d}:00-{max_hour:02d}:00 for this day."}
                )

            duration_hours = (end_dt - start_dt).seconds // 3600
            if duration_hours <= 0:
                raise serializers.ValidationError({"days": f"Shift #{idx}: duration must be at least 1 hour."})

            if mode == "office":
                total_office += duration_hours
            else:
                total_online += duration_hours

            normalized_days.append(
                {
                    "date": day_date.isoformat(),
                    "start_time": start_time.strftime("%H:%M"),
                    "end_time": end_time.strftime("%H:%M"),
                    "mode": mode,
                    "comment": item.get("comment", ""),
                }
            )

        missing = sorted(d.isoformat() for d in (expected_dates - seen_dates))
        if missing:
            raise serializers.ValidationError({"days": f"Missing shifts for dates: {', '.join(missing)}"})

        attrs["office_hours"] = total_office
        attrs["online_hours"] = total_online
        attrs["days"] = normalized_days

        needs_reason = total_office < 24 or total_online > 16
        if needs_reason and not (attrs.get("online_reason") or "").strip():
            raise serializers.ValidationError(
                {"online_reason": "Reason is required when office < 24 and/or online > 16."}
            )
        return attrs

    @staticmethod
    def _day_hour_limits(day_date):
        if day_date.weekday() < 5:
            return 9, 21
        return 11, 19


class WeeklyWorkPlanSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    reviewed_by_username = serializers.CharField(source="reviewed_by.username", read_only=True)

    class Meta:
        model = WeeklyWorkPlan
        fields = (
            "id",
            "user",
            "username",
            "week_start",
            "days",
            "office_hours",
            "online_hours",
            "online_reason",
            "employee_comment",
            "status",
            "admin_comment",
            "reviewed_by",
            "reviewed_by_username",
            "submitted_at",
            "updated_at",
            "reviewed_at",
        )
        read_only_fields = (
            "id",
            "user",
            "status",
            "admin_comment",
            "reviewed_by",
            "reviewed_by_username",
            "submitted_at",
            "updated_at",
            "reviewed_at",
        )


class WeeklyWorkPlanDecisionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(
        choices=(
            ("approve", "approve"),
            ("request_clarification", "request_clarification"),
            ("reject", "reject"),
        )
    )
    admin_comment = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        action = attrs["action"]
        comment = (attrs.get("admin_comment") or "").strip()
        if action in {"request_clarification", "reject"} and not comment:
            raise serializers.ValidationError(
                {"admin_comment": "admin_comment is required for clarification or reject."}
            )
        return attrs
