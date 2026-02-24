from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AttendanceSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("checked_at", models.DateTimeField(auto_now_add=True)),
                ("latitude", models.DecimalField(decimal_places=6, max_digits=9)),
                ("longitude", models.DecimalField(decimal_places=6, max_digits=9)),
                ("accuracy_m", models.FloatField(blank=True, null=True)),
                ("distance_m", models.FloatField()),
                ("office_latitude", models.DecimalField(decimal_places=6, max_digits=9)),
                ("office_longitude", models.DecimalField(decimal_places=6, max_digits=9)),
                ("radius_m", models.PositiveIntegerField()),
                (
                    "result",
                    models.CharField(
                        choices=[("IN_OFFICE", "In office"), ("OUTSIDE_GEOFENCE", "Outside geofence")],
                        max_length=32,
                    ),
                ),
                (
                    "attendance_mark",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="sessions",
                        to="attendance.attendancemark",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attendance_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-checked_at"],
            },
        ),
        migrations.AddIndex(
            model_name="attendancesession",
            index=models.Index(fields=["user", "checked_at"], name="attendance__user_id_66f2ac_idx"),
        ),
        migrations.AddIndex(
            model_name="attendancesession",
            index=models.Index(fields=["result"], name="attendance__result_bdea10_idx"),
        ),
        migrations.AddIndex(
            model_name="attendancesession",
            index=models.Index(fields=["checked_at"], name="attendance__checked_64e8bd_idx"),
        ),
    ]
