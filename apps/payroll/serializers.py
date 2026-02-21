from rest_framework import serializers

from .models import PayrollEntry, PayrollPeriod, SalaryProfile


class MonthQuerySerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=2000, max_value=2100)
    month = serializers.IntegerField(min_value=1, max_value=12)


class SalaryProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = SalaryProfile
        fields = (
            "id",
            "user",
            "username",
            "base_salary",
            "employment_type",
            "currency",
            "is_active",
        )


class PayrollPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollPeriod
        fields = ("id", "year", "month", "status", "created_at", "updated_at")
        read_only_fields = ("created_at", "updated_at")


class PayrollEntrySerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    period = PayrollPeriodSerializer(read_only=True)

    class Meta:
        model = PayrollEntry
        fields = (
            "id",
            "user",
            "username",
            "period",
            "planned_days",
            "worked_days",
            "advances",
            "salary_amount",
            "total_amount",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")


class PayrollGenerateSerializer(MonthQuerySerializer):
    pass


class PayrollPeriodStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=PayrollPeriod.Status.choices)

