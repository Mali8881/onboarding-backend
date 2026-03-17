from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


class Desk(models.Model):
    class Side(models.TextChoices):
        LEFT = "left", "Left"
        RIGHT = "right", "Right"

    code = models.CharField(max_length=10, unique=True)
    side = models.CharField(max_length=10, choices=Side.choices)
    row = models.PositiveSmallIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["row", "side"]
        unique_together = ("side", "row")

    def __str__(self) -> str:
        return self.code


class DeskBooking(models.Model):
    desk = models.ForeignKey(Desk, on_delete=models.CASCADE, related_name="bookings")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="desk_bookings")
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "start_time", "end_time", "-created_at"]
        unique_together = (("user", "date"),)
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["user"]),
            models.Index(fields=["desk"]),
            models.Index(fields=["desk", "date"]),
            models.Index(fields=["user", "date"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(end_time__gt=F("start_time")),
                name="desks_booking_end_after_start",
            ),
        ]

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError({"end_time": "End time must be after start time."})

    def __str__(self) -> str:
        return f"{self.desk.code} @ {self.date} {self.start_time}-{self.end_time}"


class MeetingRoom(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class MeetingRoomBooking(models.Model):
    class Purpose(models.TextChoices):
        DISCUSSION = "discussion", "Обсуждение"
        ONE_ON_ONE = "one_on_one", "1:1"
        INTERVIEW = "interview", "Собеседование"
        HR = "hr", "HR-встреча"
        PLANNING = "planning", "Планирование"
        OTHER = "other", "Другое"

    room = models.ForeignKey(MeetingRoom, on_delete=models.CASCADE, related_name="bookings")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="meeting_room_bookings")
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    purpose = models.CharField(max_length=32, choices=Purpose.choices, default=Purpose.DISCUSSION)
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="meeting_room_participations",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "start_time", "end_time", "-created_at"]
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["user"]),
            models.Index(fields=["room"]),
            models.Index(fields=["room", "date"]),
            models.Index(fields=["user", "date"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(end_time__gt=F("start_time")),
                name="meeting_room_booking_end_after_start",
            ),
        ]

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError({"end_time": "End time must be after start time."})

    def __str__(self) -> str:
        return f"{self.room.name} @ {self.date} {self.start_time}-{self.end_time}"
