from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0011_merge_20260303_1327"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="notes",
            field=models.TextField(blank=True, default="", verbose_name="Заметки / комментарий"),
        ),
    ]
