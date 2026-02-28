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
            "created_at",
            "updated_at",
        )
        read_only_fields = ("calculated_at", "paid_at", "created_at", "updated_at")


class PayrollRecordStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=PayrollRecord.Status.choices)


class HourlyRateUpdateSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    rate = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    start_date = serializers.DateField(required=False)

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
