from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0003_attendancesession_ip_address"),
    ]

    operations = [
        migrations.AddField(
            model_name="attendancemark",
            name="actual_hours",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=6,
                validators=[MinValueValidator(0)],
            ),
        ),
        migrations.AddField(
            model_name="attendancemark",
            name="planned_hours",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=6,
                validators=[MinValueValidator(0)],
            ),
        ),
    ]
