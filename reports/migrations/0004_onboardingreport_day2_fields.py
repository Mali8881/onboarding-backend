from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0003_employee_daily_report_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="onboardingreport",
            name="github_url",
            field=models.URLField(blank=True, default="", verbose_name="Ссылка на работу (GitHub)"),
        ),
        migrations.AddField(
            model_name="onboardingreport",
            name="report_description",
            field=models.TextField(blank=True, default="", verbose_name="Описание отчета"),
        ),
        migrations.AddField(
            model_name="onboardingreport",
            name="report_title",
            field=models.CharField(blank=True, default="", max_length=255, verbose_name="Название отчета"),
        ),
    ]
