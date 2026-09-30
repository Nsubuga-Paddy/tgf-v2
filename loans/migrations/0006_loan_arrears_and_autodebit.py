from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("loans", "0005_memberloan_disbursement_fees"),
    ]

    operations = [
        migrations.AddField(
            model_name="loanapplication",
            name="auto_debit",
            field=models.BooleanField(
                default=False,
                help_text="If approved, debit the monthly installment from Main Account on each due date.",
            ),
        ),
        migrations.AddField(
            model_name="memberloan",
            name="arrears_interest",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                help_text="Extra monthly interest accrued after the agreed term, charged on original principal.",
                max_digits=14,
            ),
        ),
        migrations.AddField(
            model_name="memberloan",
            name="auto_debit",
            field=models.BooleanField(
                default=False,
                help_text="Debit the monthly installment from Main Account on each due date.",
            ),
        ),
        migrations.AddField(
            model_name="memberloan",
            name="overdue_since",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="memberloan",
            name="last_arrears_accrual_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="memberloan",
            name="first_overdue_notice_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="memberloan",
            name="last_member_reminder_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="memberloan",
            name="last_auto_debit_at",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="memberloan",
            name="last_auto_debit_failure_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="loaninstallment",
            name="auto_debit_attempted_on",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="loaninstallment",
            name="status",
            field=models.CharField(
                choices=[
                    ("paid", "Paid"),
                    ("due", "Due now"),
                    ("overdue", "Overdue"),
                    ("upcoming", "Upcoming"),
                ],
                db_index=True,
                default="upcoming",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="loanrepayment",
            name="method",
            field=models.CharField(
                choices=[
                    ("main_account", "Main Account"),
                    ("bank_transfer", "Bank transfer"),
                    ("auto_debit", "Automatic Main Account debit"),
                ],
                max_length=30,
            ),
        ),
        migrations.CreateModel(
            name="LoanArrearsCharge",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("accrued_on", models.DateField()),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "loan",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="arrears_charges",
                        to="loans.memberloan",
                    ),
                ),
            ],
            options={
                "verbose_name": "Loan arrears charge",
                "verbose_name_plural": "Loan arrears charges",
                "ordering": ["-accrued_on", "-id"],
            },
        ),
        migrations.CreateModel(
            name="LoanOpsState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("last_staff_digest_on", models.DateField(blank=True, null=True)),
            ],
            options={
                "verbose_name": "Loan operations state",
                "verbose_name_plural": "Loan operations state",
            },
        ),
    ]
