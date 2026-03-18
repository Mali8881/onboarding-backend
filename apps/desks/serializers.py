from rest_framework import serializers

from .models import Desk, DeskBooking, MeetingRoom, MeetingRoomBooking


class DeskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Desk
        fields = ("id", "code", "side", "row")


class DeskBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeskBooking
        fields = ("id", "desk", "user", "date", "start_time", "end_time", "created_at")
        read_only_fields = fields


class DeskBookingCreateSerializer(serializers.Serializer):
    desk_id = serializers.IntegerField()
    date = serializers.DateField()
    start_time = serializers.TimeField(format="%H:%M", input_formats=["%H:%M"], required=False, allow_null=True)
    end_time = serializers.TimeField(format="%H:%M", input_formats=["%H:%M"], required=False, allow_null=True)

    def validate(self, attrs):
        start_time = attrs.get("start_time")
        end_time = attrs.get("end_time")

        if (start_time is None) != (end_time is None):
            raise serializers.ValidationError("start_time and end_time must be provided together.")
        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError("end_time must be after start_time.")
        return attrs


class MeetingRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetingRoom
        fields = ("id", "name")


class MeetingRoomBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetingRoomBooking
        fields = ("id", "room", "user", "date", "start_time", "end_time", "purpose", "participants", "created_at")
        read_only_fields = fields


class MeetingRoomBookingCreateSerializer(serializers.Serializer):
    room_id = serializers.IntegerField()
    date = serializers.DateField()
    start_time = serializers.TimeField(format="%H:%M", input_formats=["%H:%M"])
    end_time = serializers.TimeField(format="%H:%M", input_formats=["%H:%M"], required=False, allow_null=True)
    purpose = serializers.ChoiceField(choices=MeetingRoomBooking.Purpose.choices)
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
    )

    def validate(self, attrs):
        start_time = attrs.get("start_time")
        end_time = attrs.get("end_time")
        if end_time and end_time <= start_time:
            raise serializers.ValidationError("end_time must be after start_time.")
        return attrs
