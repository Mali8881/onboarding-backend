from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_department_parent"),
        ("regulations", "0002_regulation_updated_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="regulation",
            name="is_mandatory_on_day_one",
            field=models.BooleanField(
                default=False,
                verbose_name="Обязателен в первый день стажировки",
            ),
        ),
        migrations.CreateModel(
            name="RegulationAcknowledgement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("acknowledged_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата ознакомления")),
                ("user_full_name", models.CharField(max_length=255, verbose_name="ФИО пользователя")),
                ("regulation_title", models.CharField(max_length=255, verbose_name="Название документа")),
                (
                    "regulation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="acknowledgements",
                        to="regulations.regulation",
                        verbose_name="Регламент",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="regulation_acknowledgements",
                        to="accounts.user",
                        verbose_name="Пользователь",
                    ),
                ),
            ],
            options={
                "verbose_name": "Ознакомление с регламентом",
                "verbose_name_plural": "Ознакомления с регламентами",
                "ordering": ["-acknowledged_at"],
                "unique_together": {("user", "regulation")},
            },
        ),
    ]

