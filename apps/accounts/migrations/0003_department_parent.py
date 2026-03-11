from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_rbac_org_refactor"),
    ]

    operations = [
        migrations.AddField(
            model_name="department",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="children",
                to="accounts.department",
            ),
        ),
    ]

