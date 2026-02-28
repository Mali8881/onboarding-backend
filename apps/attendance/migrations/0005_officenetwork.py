from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0004_attendancemark_planned_actual_hours"),
    ]

    operations = [
        migrations.CreateModel(
            name="OfficeNetwork",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150)),
                ("cidr", models.CharField(max_length=64, unique=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["name", "id"],
                "indexes": [
                    models.Index(fields=["is_active"], name="attendance__is_acti_0be24a_idx"),
                    models.Index(fields=["cidr"], name="attendance__cidr_a4140a_idx"),
                ],
            },
        ),
    ]
