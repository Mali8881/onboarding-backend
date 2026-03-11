from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("regulations", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="regulation",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, null=True),
        ),
    ]

