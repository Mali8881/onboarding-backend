from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="permission",
            old_name="code",
            new_name="codename",
        ),
        migrations.AddField(
            model_name="permission",
            name="module",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="role",
            name="level",
            field=models.PositiveSmallIntegerField(
                choices=[(10, "Intern"), (20, "Employee"), (30, "Admin"), (40, "SuperAdmin")],
                default=10,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="manager",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="team_members",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
