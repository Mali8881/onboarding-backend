import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_user_intern_onboarding_fields"),
        ("reports", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="EmployeeDailyReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("report_date", models.DateField()),
                ("summary", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="employee_daily_reports", to="accounts.user")),
            ],
            options={
                "ordering": ["-report_date", "-updated_at"],
                "unique_together": {("user", "report_date")},
            },
        ),
    ]
