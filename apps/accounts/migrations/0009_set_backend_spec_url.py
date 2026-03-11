from django.db import migrations


BACKEND_SPEC_URL = "https://docs.google.com/document/d/1cVfZKJX_XcIgYkxb0f5YT5pSiqBP1WJY6FRJ6rPZfJg/edit?tab=t.0"


def forwards(apps, schema_editor):
    DepartmentSubdivision = apps.get_model("accounts", "DepartmentSubdivision")
    DepartmentSubdivision.objects.filter(
        name__iexact="Бэкенд разработчик"
    ).update(day_two_spec_url=BACKEND_SPEC_URL)


def backwards(apps, schema_editor):
    DepartmentSubdivision = apps.get_model("accounts", "DepartmentSubdivision")
    DepartmentSubdivision.objects.filter(
        name__iexact="Бэкенд разработчик",
        day_two_spec_url=BACKEND_SPEC_URL,
    ).update(day_two_spec_url="")


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0008_seed_default_subdivisions"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
