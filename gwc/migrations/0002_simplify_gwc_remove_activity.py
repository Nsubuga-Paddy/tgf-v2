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


def ensure_fixed_deposit_table_exists(apps, schema_editor):
    """
    Some environments have gwc.0001 recorded in django_migrations but are missing
    physical tables (typically from historical/fake migration drift). Ensure the
    base GWCFixedDeposit table exists before 0002 applies AddField/AlterField ops.
    """
    GWCFixedDeposit = apps.get_model("gwc", "GWCFixedDeposit")
    table_name = GWCFixedDeposit._meta.db_table
    conn = schema_editor.connection

    exists = False
    if conn.vendor == "postgresql":
        # Use PostgreSQL catalog lookup; more reliable than introspection caches.
        with conn.cursor() as cursor:
            cursor.execute("SELECT to_regclass(%s)", [f"public.{table_name}"])
            exists = cursor.fetchone()[0] is not None
    else:
        exists = table_name in set(conn.introspection.table_names())

    if not exists:
        schema_editor.create_model(GWCFixedDeposit)


def noop_reverse_ensure_fixed_deposit(apps, schema_editor):
    pass


def drop_gwc_deposit_activity_table_if_exists(apps, schema_editor):
    """
    Remove GWCDepositActivity table if present. Uses IF EXISTS so deploys succeed when
    0001 never created this table (e.g. 0001 was edited after being applied) or the table
    was already removed.
    """
    table = "gwc_gwcdepositactivity"
    vendor = schema_editor.connection.vendor
    if vendor == "postgresql":
        schema_editor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE;')
    else:
        # SQLite and other backends
        schema_editor.execute(f"DROP TABLE IF EXISTS {table};")


def noop_reverse_drop_activity(apps, schema_editor):
    """Recreating the dropped table on migrate backwards is not supported."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("gwc", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            ensure_fixed_deposit_table_exists,
            noop_reverse_ensure_fixed_deposit,
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name="GWCDepositActivity"),
            ],
            database_operations=[
                migrations.RunPython(
                    drop_gwc_deposit_activity_table_if_exists,
                    noop_reverse_drop_activity,
                ),
            ],
        ),
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
