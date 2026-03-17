from django.conf import settings
from django.db import migrations, models
from django.db.models import F, Q
import django.db.models.deletion


def seed_meeting_rooms(apps, schema_editor):
    MeetingRoom = apps.get_model("desks", "MeetingRoom")
    names = ["Пещера вождя", "HR", "Большой HR"]
    existing = set(MeetingRoom.objects.values_list("name", flat=True))
    MeetingRoom.objects.bulk_create([MeetingRoom(name=name) for name in names if name not in existing])


def unseed_meeting_rooms(apps, schema_editor):
    MeetingRoom = apps.get_model("desks", "MeetingRoom")
    MeetingRoom.objects.filter(name__in=["Пещера вождя", "HR", "Большой HR"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("desks", "0002_booking_time_slots"),
    ]

    operations = [
        migrations.CreateModel(
            name="MeetingRoom",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="MeetingRoomBooking",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField()),
                ("start_time", models.TimeField()),
                ("end_time", models.TimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "room",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="bookings", to="desks.meetingroom"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="meeting_room_bookings", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={"ordering": ["-date", "start_time", "end_time", "-created_at"]},
        ),
        migrations.AddIndex(
            model_name="meetingroombooking",
            index=models.Index(fields=["date"], name="desks_meeti_date_idx"),
        ),
        migrations.AddIndex(
            model_name="meetingroombooking",
            index=models.Index(fields=["user"], name="desks_meeti_user_idx"),
        ),
        migrations.AddIndex(
            model_name="meetingroombooking",
            index=models.Index(fields=["room"], name="desks_meeti_room_idx"),
        ),
        migrations.AddIndex(
            model_name="meetingroombooking",
            index=models.Index(fields=["room", "date"], name="desks_meeti_room_date_idx"),
        ),
        migrations.AddIndex(
            model_name="meetingroombooking",
            index=models.Index(fields=["user", "date"], name="desks_meeti_user_date_idx"),
        ),
        migrations.AddConstraint(
            model_name="meetingroombooking",
            constraint=models.CheckConstraint(
                check=Q(end_time__gt=F("start_time")),
                name="meeting_room_booking_end_after_start",
            ),
        ),
        migrations.RunPython(seed_meeting_rooms, unseed_meeting_rooms),
    ]
