from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0006_role_hierarchy_update"),
    ]

    operations = [
        migrations.CreateModel(
            name="DepartmentSubdivision",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150, verbose_name="Название")),
                (
                    "day_two_task_title",
                    models.CharField(blank=True, max_length=255, verbose_name="Заголовок задачи 2-го дня"),
                ),
                ("day_two_task_description", models.TextField(blank=True, verbose_name="Описание задачи 2-го дня")),
                ("day_two_spec_url", models.URLField(blank=True, verbose_name="Ссылка на ТЗ/документ")),
                ("is_active", models.BooleanField(default=True, verbose_name="Активен")),
                (
                    "department",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subdivisions",
                        to="accounts.department",
                        verbose_name="Отдел",
                    ),
                ),
            ],
            options={
                "verbose_name": "Подотдел",
                "verbose_name_plural": "Подотделы",
                "ordering": ["department__name", "name"],
                "unique_together": {("department", "name")},
            },
        ),
        migrations.AddField(
            model_name="user",
            name="subdivision",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="users",
                to="accounts.departmentsubdivision",
                verbose_name="Подотдел",
            ),
        ),
    ]
