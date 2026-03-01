from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0002_employee_daily_report"),
    ]

    operations = [
        migrations.AddField(
            model_name="employeedailyreport",
            name="blockers",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="employeedailyreport",
            name="completed_tasks",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="employeedailyreport",
            name="started_tasks",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="employeedailyreport",
            name="taken_tasks",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="employeedailyreport",
            name="summary",
            field=models.TextField(blank=True, default=""),
        ),
    ]
