from rest_framework import serializers


class CalendarDaySerializer(serializers.Serializer):
    date = serializers.DateField()
    weekday = serializers.IntegerField()
    is_working_day = serializers.BooleanField()
    is_holiday = serializers.BooleanField()
    holiday_name = serializers.CharField(allow_blank=True)
    work_time = serializers.DictField(allow_null=True)
    break_time = serializers.DictField(allow_null=True)
