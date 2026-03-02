from datetime import date

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import HourlyRateHistory, PayrollCompensation, PayrollRecord


User = get_user_model()


class MonthQuerySerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=2000, max_value=2100)
    month = serializers.IntegerField(min_value=1, max_value=12)


class PayrollRecalculateSerializer(MonthQuerySerializer):
    pass


class PayrollRecordSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    is_calculated = serializers.BooleanField(read_only=True, default=True)

    class Meta:
        model = PayrollRecord
        fields = (
            "id",
            "user",
            "username",
            "month",
            "total_hours",
            "total_salary",
            "bonus",
            "status",
            "calculated_at",
            "paid_at",
            "is_calculated",
        )
        read_only_fields = ("calculated_at", "paid_at", "is_calculated")


class PayrollRecordStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=PayrollRecord.Status.choices)


class HourlyRateUpdateSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    rate = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    start_date = serializers.DateField(required=False)

    def to_internal_value(self, data):
        payload = dict(data)

        if "user_id" not in payload:
            for key in ("userId", "user", "employee_id"):
                if key in data and data.get(key) not in (None, ""):
                    payload["user_id"] = data.get(key)
                    break

        if "rate" not in payload:
            for key in ("hourly_rate", "hourlyRate"):
                if key in data and data.get(key) not in (None, ""):
                    payload["rate"] = data.get(key)
                    break

        return super().to_internal_value(payload)

    def validate_user_id(self, value: int):
        if not User.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("User not found.")
        return value

    def validate_start_date(self, value: date):
        if value.year < 2000 or value.year > 2100:
            raise serializers.ValidationError("Invalid start_date.")
        return value


class PayrollCompensationUpdateSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    pay_type = serializers.ChoiceField(choices=PayrollCompensation.PayType.choices)
    hourly_rate = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, required=False)
    minute_rate = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, required=False)
    fixed_salary = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, required=False)
    start_date = serializers.DateField(required=False)

    def to_internal_value(self, data):
        payload = dict(data)

        if "user_id" not in payload:
            for key in ("userId", "user", "employee_id"):
                if key in data and data.get(key) not in (None, ""):
                    payload["user_id"] = data.get(key)
                    break

        if "pay_type" not in payload:
            for key in ("payModel", "pay_model", "model", "type"):
                if key in data and data.get(key) not in (None, ""):
                    payload["pay_type"] = data.get(key)
                    break

        if "hourly_rate" not in payload and "hourlyRate" in data:
            payload["hourly_rate"] = data.get("hourlyRate")
        if "minute_rate" not in payload and "minuteRate" in data:
            payload["minute_rate"] = data.get("minuteRate")
        if "fixed_salary" not in payload and "fixedSalary" in data:
            payload["fixed_salary"] = data.get("fixedSalary")

        if "pay_type" not in payload or payload.get("pay_type") in (None, ""):
            if payload.get("fixed_salary") not in (None, ""):
                payload["pay_type"] = PayrollCompensation.PayType.FIXED_SALARY
            elif payload.get("minute_rate") not in (None, ""):
                payload["pay_type"] = PayrollCompensation.PayType.MINUTE
            elif payload.get("hourly_rate") not in (None, ""):
                payload["pay_type"] = PayrollCompensation.PayType.HOURLY

        return super().to_internal_value(payload)

    def validate_user_id(self, value: int):
        if not User.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("User not found.")
        return value

    def validate(self, attrs):
        pay_type = attrs["pay_type"]
        if pay_type == PayrollCompensation.PayType.HOURLY and "hourly_rate" not in attrs:
            raise serializers.ValidationError({"hourly_rate": "hourly_rate is required for hourly pay type."})
        if pay_type == PayrollCompensation.PayType.MINUTE and "minute_rate" not in attrs:
            raise serializers.ValidationError({"minute_rate": "minute_rate is required for minute pay type."})
        if pay_type == PayrollCompensation.PayType.FIXED_SALARY and "fixed_salary" not in attrs:
            raise serializers.ValidationError({"fixed_salary": "fixed_salary is required for fixed salary pay type."})
        return attrs


class PayrollCompensationSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    role = serializers.CharField(source="user.role.name", read_only=True)
    current_hourly_rate = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = PayrollCompensation
        fields = (
            "user",
            "username",
            "role",
            "pay_type",
            "hourly_rate",
            "minute_rate",
            "fixed_salary",
            "current_hourly_rate",
            "updated_at",
        )


class HourlyRateHistorySerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = HourlyRateHistory
        fields = ("id", "user", "username", "rate", "start_date", "created_at")
        read_only_fields = ("created_at",)
