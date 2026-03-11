from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_rbac_org_refactor"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="intern_onboarding_completed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="intern_onboarding_started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
