from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


def cleanup_withdraw_ledger_rows(apps, schema_editor):
    ShareAcquisitionLine = apps.get_model(
        "cooperative_shareholding", "ShareAcquisitionLine"
    )
    ShareAcquisitionLine.objects.filter(
        receipt_number__startswith="DIV-",
        shares_held=0,
    ).delete()


def backfill_disbursements(apps, schema_editor):
    DividendChoiceRequest = apps.get_model(
        "cooperative_shareholding", "DividendChoiceRequest"
    )
    DividendAllocationLine = apps.get_model(
        "cooperative_shareholding", "DividendAllocationLine"
    )
    DividendDisbursement = apps.get_model(
        "cooperative_shareholding", "DividendDisbursement"
    )
    fulfillment_map = {
        "cash": "cash_paid",
        "mcs_shares": "mcs_reinvest",
        "mesu_shares": "mesu_reinvest",
        "savings": "savings_deposit",
    }
    for submission in DividendChoiceRequest.objects.filter(
        ledger_applied_at__isnull=False
    ):
        when = submission.ledger_applied_at or timezone.now()
        for line in DividendAllocationLine.objects.filter(submission=submission):
            if DividendDisbursement.objects.filter(allocation_line=line).exists():
                continue
            DividendDisbursement.objects.create(
                shareholding_id=submission.shareholding_id,
                submission=submission,
                allocation_line=line,
                fulfillment_type=fulfillment_map.get(
                    line.action_type, "cash_paid"
                ),
                amount=line.amount,
                shares_count=line.shares_count or 0,
                disbursed_at=when,
                notes=line.action_type,
            )


class Migration(migrations.Migration):

    dependencies = [
        (
            "cooperative_shareholding",
            "0006_alter_cooperativeglobaldefaults_blue_diamond_usd_threshold_and_more",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="DividendDisbursement",
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
                    "fulfillment_type",
                    models.CharField(
                        choices=[
                            ("cash_paid", "Cash paid (MoMo / bank)"),
                            ("mcs_reinvest", "Reinvested in MCS shares"),
                            ("mesu_reinvest", "Reinvested in MESU Academy shares"),
                            ("savings_deposit", "Fixed / compulsory deposit"),
                        ],
                        max_length=20,
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=2, max_digits=16)),
                ("shares_count", models.PositiveIntegerField(default=0)),
                ("disbursed_at", models.DateTimeField()),
                (
                    "payment_reference",
                    models.CharField(
                        blank=True,
                        help_text="MoMo / bank reference when paid manually.",
                        max_length=120,
                    ),
                ),
                ("notes", models.CharField(blank=True, max_length=255)),
                (
                    "allocation_line",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="disbursement",
                        to="cooperative_shareholding.dividendallocationline",
                    ),
                ),
                (
                    "shareholding",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dividend_disbursements",
                        to="cooperative_shareholding.cooperativeshareholding",
                    ),
                ),
                (
                    "submission",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="disbursements",
                        to="cooperative_shareholding.dividendchoicerequest",
                    ),
                ),
            ],
            options={
                "verbose_name": "Dividend disbursement",
                "verbose_name_plural": "Dividend disbursements",
                "ordering": ["-disbursed_at", "-pk"],
            },
        ),
        migrations.RunPython(cleanup_withdraw_ledger_rows, migrations.RunPython.noop),
        migrations.RunPython(backfill_disbursements, migrations.RunPython.noop),
    ]
