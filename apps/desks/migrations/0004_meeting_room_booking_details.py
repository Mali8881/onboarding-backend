from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("desks", "0003_meeting_rooms"),
    ]

    operations = [
        migrations.AddField(
            model_name="meetingroombooking",
            name="participants",
            field=models.ManyToManyField(
                blank=True,
                related_name="meeting_room_participations",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="meetingroombooking",
            name="purpose",
            field=models.CharField(
                choices=[
                    ("discussion", "Обсуждение"),
                    ("one_on_one", "1:1"),
                    ("interview", "Собеседование"),
                    ("hr", "HR-встреча"),
                    ("planning", "Планирование"),
                    ("other", "Другое"),
                ],
                default="discussion",
                max_length=32,
            ),
        ),
    ]
