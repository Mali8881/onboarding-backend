from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0002_attendancesession"),
    ]

    operations = [
        migrations.AddField(
            model_name="attendancesession",
            name="ip_address",
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
    ]
