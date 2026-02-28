from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("payroll", "0003_payrollentry_bonus"),
    ]

    operations = [
        migrations.DeleteModel(
            name="PayrollEntry",
        ),
        migrations.DeleteModel(
            name="PayrollSettings",
        ),
        migrations.DeleteModel(
            name="SalaryProfile",
        ),
        migrations.DeleteModel(
            name="PayrollPeriod",
        ),
        migrations.CreateModel(
            name="HourlyRateHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("rate", models.DecimalField(decimal_places=2, max_digits=12, validators=[MinValueValidator(0)])),
                ("start_date", models.DateField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="hourly_rate_history",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-start_date", "-id"],
                "indexes": [models.Index(fields=["user", "start_date"], name="payroll_hou_user_id_ba6f62_idx"), models.Index(fields=["start_date"], name="payroll_hou_start_d_5f1392_idx")],
                "constraints": [
                    models.UniqueConstraint(fields=("user", "start_date"), name="payroll_unique_rate_user_start_date"),
                ],
            },
        ),
        migrations.CreateModel(
            name="PayrollRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("month", models.DateField(help_text="First day of payroll month")),
                ("total_hours", models.DecimalField(decimal_places=2, default=0, max_digits=8, validators=[MinValueValidator(0)])),
                ("total_salary", models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[MinValueValidator(0)])),
                ("bonus", models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[MinValueValidator(0)])),
                ("status", models.CharField(choices=[("calculated", "Calculated"), ("paid", "Paid")], default="calculated", max_length=20)),
                ("calculated_at", models.DateTimeField(auto_now=True)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payroll_records",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["month", "user_id"],
                "indexes": [
                    models.Index(fields=["month"], name="payroll_pay_month_1bfe22_idx"),
                    models.Index(fields=["status"], name="payroll_pay_status_7fdcf4_idx"),
                    models.Index(fields=["user", "month"], name="payroll_pay_user_id_76cbf4_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(fields=("user", "month"), name="payroll_unique_record_user_month"),
                ],
            },
        ),
    ]
