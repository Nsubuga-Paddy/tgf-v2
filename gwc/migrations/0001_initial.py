# Generated manually for GWC fixed deposits

import django.db.models.deletion
import django.utils.timezone
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="GWCFixedDeposit",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "deposit_id",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        editable=False,
                        help_text="Auto-generated public reference (e.g. GWC-2026-00042).",
                        max_length=32,
                        unique=True,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("Active", "Active"),
                            ("Matured", "Matured"),
                            ("Withdrawn", "Withdrawn"),
                            ("Cancelled", "Cancelled"),
                        ],
                        db_index=True,
                        default="Active",
                        max_length=20,
                    ),
                ),
                (
                    "principal_amount",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Principal in UGX.",
                        max_digits=16,
                    ),
                ),
                (
                    "interest_rate",
                    models.DecimalField(
                        decimal_places=4,
                        help_text="Nominal annual interest rate (%).",
                        max_digits=7,
                    ),
                ),
                (
                    "interest_method",
                    models.CharField(
                        choices=[
                            ("simple", "Simple"),
                            ("compound", "Compound"),
                        ],
                        default="simple",
                        max_length=20,
                    ),
                ),
                (
                    "compounding_frequency",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("daily", "Daily"),
                            ("monthly", "Monthly"),
                            ("quarterly", "Quarterly"),
                            ("annually", "Annually"),
                        ],
                        default="",
                        help_text="Used when interest method is compound.",
                        max_length=20,
                    ),
                ),
                ("start_date", models.DateField(db_index=True)),
                ("maturity_date", models.DateField(db_index=True)),
                (
                    "tax_rate",
                    models.DecimalField(
                        decimal_places=4,
                        default=Decimal("0"),
                        help_text="Withholding / tax on interest (% of gross interest).",
                        max_digits=7,
                    ),
                ),
                ("auto_renewal", models.BooleanField(default=False)),
                (
                    "minimum_lock_period_days",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Minimum days before early withdrawal (informational / policy).",
                    ),
                ),
                (
                    "early_withdrawal_penalty",
                    models.DecimalField(
                        decimal_places=4,
                        default=Decimal("0"),
                        help_text="Penalty as % of principal or accrued (policy display).",
                        max_digits=7,
                    ),
                ),
                (
                    "payout_structure_display",
                    models.CharField(
                        blank=True,
                        default="At maturity",
                        help_text="Short label shown on the member dashboard (e.g. At maturity).",
                        max_length=160,
                    ),
                ),
                (
                    "notes",
                    models.TextField(
                        blank=True,
                        help_text="Internal admin notes.",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="gwc_fixed_deposits",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "GWC fixed deposit",
                "verbose_name_plural": "GWC fixed deposits",
                "ordering": ("-start_date", "-pk"),
            },
        ),
        migrations.AddIndex(
            model_name="gwcfixeddeposit",
            index=models.Index(fields=["user", "status"], name="gwc_fd_user_status_idx"),
        ),
        migrations.CreateModel(
            name="GWCDepositActivity",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("description", models.CharField(max_length=255)),
                (
                    "activity_type",
                    models.CharField(
                        choices=[
                            ("credit", "Credit"),
                            ("debit", "Debit"),
                            ("info", "Info"),
                        ],
                        default="info",
                        max_length=20,
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="UGX amount when applicable.",
                        max_digits=16,
                        null=True,
                    ),
                ),
                (
                    "timestamp",
                    models.DateTimeField(
                        db_index=True,
                        default=django.utils.timezone.now,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "deposit",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="activities",
                        to="gwc.gwcfixeddeposit",
                    ),
                ),
            ],
            options={
                "verbose_name": "GWC deposit activity",
                "verbose_name_plural": "GWC deposit activities",
                "ordering": ("-timestamp", "-pk"),
            },
        ),
    ]
