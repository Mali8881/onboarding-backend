from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="event_key",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="notification",
            name="expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="notification",
            name="is_pinned",
            field=models.BooleanField(default=False),
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["is_pinned"], name="common_noti_is_pinne_85f7dd_idx"),
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["event_key"], name="common_noti_event_k_8baf4d_idx"),
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["expires_at"], name="common_noti_expires_81754b_idx"),
        ),
    ]
