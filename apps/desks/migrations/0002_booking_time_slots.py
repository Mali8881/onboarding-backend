from datetime import time

from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):

    dependencies = [
        ("desks", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="deskbooking",
            name="end_time",
            field=models.TimeField(default=time(18, 0)),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="deskbooking",
            name="start_time",
            field=models.TimeField(default=time(9, 0)),
            preserve_default=False,
        ),
        migrations.AlterModelOptions(
            name="deskbooking",
            options={"ordering": ["-date", "start_time", "end_time", "-created_at"]},
        ),
        migrations.AlterUniqueTogether(
            name="deskbooking",
            unique_together={("user", "date")},
        ),
        migrations.AddIndex(
            model_name="deskbooking",
            index=models.Index(fields=["desk", "date"], name="desks_deskb_desk_date_idx"),
        ),
        migrations.AddIndex(
            model_name="deskbooking",
            index=models.Index(fields=["user", "date"], name="desks_deskb_user_date_idx"),
        ),
        migrations.AddConstraint(
            model_name="deskbooking",
            constraint=models.CheckConstraint(
                check=Q(end_time__gt=F("start_time")),
                name="desks_booking_end_after_start",
            ),
        ),
    ]
