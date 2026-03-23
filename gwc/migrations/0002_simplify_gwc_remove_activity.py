# Simplify GWC: remove activity model, add receipt/transaction dates, new defaults.

from decimal import Decimal

from django.db import migrations, models


def backfill_receipt_and_transaction(apps, schema_editor):
    GWCFixedDeposit = apps.get_model("gwc", "GWCFixedDeposit")
    for d in GWCFixedDeposit.objects.all():
        updates = {}
        if getattr(d, "receipt_number", None) in (None, ""):
            updates["receipt_number"] = f"LEGACY-{d.pk}"
        if getattr(d, "transaction_date", None) is None and d.start_date:
            updates["transaction_date"] = d.start_date
        if updates:
            GWCFixedDeposit.objects.filter(pk=d.pk).update(**updates)
    # Align legacy rows with new product defaults where unset
    GWCFixedDeposit.objects.filter(tax_rate=Decimal("0")).update(tax_rate=Decimal("15"))
    GWCFixedDeposit.objects.filter(
        interest_method="compound", compounding_frequency=""
    ).update(compounding_frequency="annually")


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("gwc", "0001_initial"),
    ]

    operations = [
        migrations.DeleteModel(name="GWCDepositActivity"),
        migrations.AddField(
            model_name="gwcfixeddeposit",
            name="receipt_number",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Physical / admin receipt reference for this deposit.",
                max_length=64,
            ),
        ),
        migrations.AddField(
            model_name="gwcfixeddeposit",
            name="transaction_date",
            field=models.DateField(
                blank=True,
                help_text="Date the deposit transaction was recorded / received.",
                null=True,
            ),
        ),
        migrations.RunPython(backfill_receipt_and_transaction, noop_reverse),
        migrations.AlterField(
            model_name="gwcfixeddeposit",
            name="receipt_number",
            field=models.CharField(
                help_text="Physical / admin receipt reference for this deposit.",
                max_length=64,
            ),
        ),
        migrations.AlterField(
            model_name="gwcfixeddeposit",
            name="transaction_date",
            field=models.DateField(
                help_text="Date the deposit transaction was recorded / received.",
            ),
        ),
        migrations.AlterField(
            model_name="gwcfixeddeposit",
            name="interest_rate",
            field=models.DecimalField(
                decimal_places=4,
                default=Decimal("25"),
                help_text="Nominal annual interest rate (%).",
                max_digits=7,
            ),
        ),
        migrations.AlterField(
            model_name="gwcfixeddeposit",
            name="interest_method",
            field=models.CharField(
                choices=[("simple", "Simple"), ("compound", "Compound")],
                default="compound",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="gwcfixeddeposit",
            name="compounding_frequency",
            field=models.CharField(
                choices=[
                    ("daily", "Daily"),
                    ("monthly", "Monthly"),
                    ("quarterly", "Quarterly"),
                    ("annually", "Annually"),
                ],
                default="annually",
                help_text="Used when interest method is compound.",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="gwcfixeddeposit",
            name="tax_rate",
            field=models.DecimalField(
                decimal_places=4,
                default=Decimal("15"),
                help_text="Withholding on interest (% of gross). Used internally at withdrawal; not shown on member dashboard.",
                max_digits=7,
            ),
        ),
        migrations.AlterField(
            model_name="gwcfixeddeposit",
            name="start_date",
            field=models.DateField(
                db_index=True,
                help_text="Fixed deposit period start (interest accrual start).",
            ),
        ),
        migrations.AlterField(
            model_name="gwcfixeddeposit",
            name="payout_structure_display",
            field=models.CharField(
                blank=True,
                default="At maturity",
                help_text="Short label shown on the member dashboard.",
                max_length=160,
            ),
        ),
    ]
