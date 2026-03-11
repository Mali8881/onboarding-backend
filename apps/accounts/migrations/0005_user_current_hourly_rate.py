from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_merge_0003_branches"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="current_hourly_rate",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=12,
                validators=[MinValueValidator(0)],
            ),
        ),
    ]
