from rest_framework import serializers


class CalendarDaySerializer(serializers.Serializer):
    date = serializers.DateField()
    is_working_day = serializers.BooleanField()
    is_holiday = serializers.BooleanField()
    work_start = serializers.TimeField(allow_null=True)
    work_end = serializers.TimeField(allow_null=True)
