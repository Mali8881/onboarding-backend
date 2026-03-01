from datetime import datetime
from datetime import timedelta

from rest_framework import serializers

from .models import WeeklyWorkPlan, WeeklyWorkPlanChangeLog, WorkSchedule, UserWorkSchedule


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


class ShiftBreakSerializer(serializers.Serializer):
    start_time = serializers.TimeField(format="%H:%M", input_formats=["%H:%M"])
    end_time = serializers.TimeField(format="%H:%M", input_formats=["%H:%M"])


class WeeklyWorkPlanUpsertSerializer(serializers.Serializer):
    class ShiftSerializer(serializers.Serializer):
        date = serializers.DateField()
        start_time = serializers.TimeField(format="%H:%M", input_formats=["%H:%M"], required=False, allow_null=True)
        end_time = serializers.TimeField(format="%H:%M", input_formats=["%H:%M"], required=False, allow_null=True)
        mode = serializers.ChoiceField(choices=("office", "online", "day_off"))
        comment = serializers.CharField(required=False, allow_blank=True)
        breaks = ShiftBreakSerializer(many=True, required=False)
        lunch_start = serializers.TimeField(
            format="%H:%M",
            input_formats=["%H:%M"],
            required=False,
            allow_null=True,
        )
        lunch_end = serializers.TimeField(
            format="%H:%M",
            input_formats=["%H:%M"],
            required=False,
            allow_null=True,
        )

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
            breaks = item.get("breaks") or []
            lunch_start = item.get("lunch_start")
            lunch_end = item.get("lunch_end")

            if mode == "day_off":
                if (
                    start_time is not None
                    or end_time is not None
                    or breaks
                    or lunch_start is not None
                    or lunch_end is not None
                ):
                    raise serializers.ValidationError({"days": f"Shift #{idx}: day_off must not contain start/end time."})
                normalized_days.append(
                    {
                        "date": day_date.isoformat(),
                        "start_time": None,
                        "end_time": None,
                        "mode": mode,
                        "comment": item.get("comment", ""),
                        "breaks": [],
                        "lunch_start": None,
                        "lunch_end": None,
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

            if mode == "online":
                if breaks or lunch_start is not None or lunch_end is not None:
                    raise serializers.ValidationError({"days": f"Shift #{idx}: breaks/lunch are allowed only for office mode."})
            else:
                self._validate_office_breaks_and_lunch(
                    idx=idx,
                    start_time=start_time,
                    end_time=end_time,
                    duration_hours=duration_hours,
                    breaks=breaks,
                    lunch_start=lunch_start,
                    lunch_end=lunch_end,
                )

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
                    "breaks": [
                        {
                            "start_time": break_item["start_time"].strftime("%H:%M"),
                            "end_time": break_item["end_time"].strftime("%H:%M"),
                        }
                        for break_item in breaks
                    ],
                    "lunch_start": lunch_start.strftime("%H:%M") if lunch_start else None,
                    "lunch_end": lunch_end.strftime("%H:%M") if lunch_end else None,
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

    @staticmethod
    def _to_minutes(value):
        return value.hour * 60 + value.minute

    def _validate_office_breaks_and_lunch(
        self,
        *,
        idx,
        start_time,
        end_time,
        duration_hours,
        breaks,
        lunch_start,
        lunch_end,
    ):
        if duration_hours < 7 and breaks:
            raise serializers.ValidationError({"days": f"Shift #{idx}: breaks are allowed only when office shift is 7+ hours."})
        if duration_hours < 8 and (lunch_start is not None or lunch_end is not None):
            raise serializers.ValidationError({"days": f"Shift #{idx}: lunch is allowed only when office shift is 8+ hours."})

        if (lunch_start is None) != (lunch_end is None):
            raise serializers.ValidationError({"days": f"Shift #{idx}: lunch_start and lunch_end must be set together."})

        shift_start = self._to_minutes(start_time)
        shift_end = self._to_minutes(end_time)
        intervals = []

        if breaks:
            if len(breaks) > 4:
                raise serializers.ValidationError({"days": f"Shift #{idx}: no more than 4 short breaks are allowed."})
            for break_idx, break_item in enumerate(breaks, start=1):
                b_start = break_item["start_time"]
                b_end = break_item["end_time"]
                if b_start.second or b_end.second:
                    raise serializers.ValidationError({"days": f"Shift #{idx}: break #{break_idx} must be in HH:MM format."})
                if (b_start.minute % 15) != 0 or (b_end.minute % 15) != 0:
                    raise serializers.ValidationError({"days": f"Shift #{idx}: break #{break_idx} must use 15-minute slots."})
                b_start_m = self._to_minutes(b_start)
                b_end_m = self._to_minutes(b_end)
                if b_end_m <= b_start_m:
                    raise serializers.ValidationError({"days": f"Shift #{idx}: break #{break_idx} end must be after start."})
                if (b_end_m - b_start_m) != 15:
                    raise serializers.ValidationError({"days": f"Shift #{idx}: each short break must be exactly 15 minutes."})
                if b_start_m < shift_start or b_end_m > shift_end:
                    raise serializers.ValidationError({"days": f"Shift #{idx}: break #{break_idx} must be inside shift time."})
                intervals.append((b_start_m, b_end_m, f"break #{break_idx}"))

        if lunch_start is not None and lunch_end is not None:
            if lunch_start.second or lunch_end.second:
                raise serializers.ValidationError({"days": f"Shift #{idx}: lunch must be in HH:MM format."})
            if (lunch_start.minute % 15) != 0 or (lunch_end.minute % 15) != 0:
                raise serializers.ValidationError({"days": f"Shift #{idx}: lunch must use 15-minute slots."})
            lunch_start_m = self._to_minutes(lunch_start)
            lunch_end_m = self._to_minutes(lunch_end)
            if lunch_end_m <= lunch_start_m:
                raise serializers.ValidationError({"days": f"Shift #{idx}: lunch end must be after lunch start."})
            if (lunch_end_m - lunch_start_m) != 60:
                raise serializers.ValidationError({"days": f"Shift #{idx}: lunch must be exactly 60 minutes."})
            if lunch_start_m < shift_start or lunch_end_m > shift_end:
                raise serializers.ValidationError({"days": f"Shift #{idx}: lunch must be inside shift time."})
            intervals.append((lunch_start_m, lunch_end_m, "lunch"))

        intervals.sort(key=lambda row: row[0])
        prev_end = None
        prev_label = None
        for start_m, end_m, label in intervals:
            if prev_end is not None and start_m < prev_end:
                raise serializers.ValidationError({"days": f"Shift #{idx}: {label} overlaps with {prev_label}."})
            prev_end = end_m
            prev_label = label


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


class WeeklyWorkPlanChangeLogSerializer(serializers.ModelSerializer):
    changed_by_username = serializers.CharField(source="changed_by.username", read_only=True)

    class Meta:
        model = WeeklyWorkPlanChangeLog
        fields = (
            "id",
            "weekly_plan",
            "user",
            "week_start",
            "changes",
            "changed_by",
            "changed_by_username",
            "created_at",
        )
