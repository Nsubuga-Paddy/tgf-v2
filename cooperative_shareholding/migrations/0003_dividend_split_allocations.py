from decimal import Decimal

from django.db import migrations, models


def migrate_legacy_dividend_choices(apps, schema_editor):
    DividendChoiceRequest = apps.get_model(
        "cooperative_shareholding", "DividendChoiceRequest"
    )
    DividendAllocationLine = apps.get_model(
        "cooperative_shareholding", "DividendAllocationLine"
    )
    for submission in DividendChoiceRequest.objects.all():
        if not hasattr(submission, "action_type"):
            continue
        action_type = submission.action_type
        if action_type == "more_shares":
            action_type = "mcs_shares"
        DividendAllocationLine.objects.create(
            submission_id=submission.pk,
            action_type=action_type,
            amount=submission.dividend_amount,
            shares_count=getattr(submission, "shares_to_reinvest", 0) or 0,
        )
        submission.total_dividend = submission.dividend_amount
        submission.save(update_fields=["total_dividend"])


class Migration(migrations.Migration):

    dependencies = [
        ("cooperative_shareholding", "0002_refactor_settings_to_shareholding"),
    ]

    operations = [
        migrations.AddField(
            model_name="dividendchoicerequest",
            name="total_dividend",
            field=models.DecimalField(
                decimal_places=2,
                help_text="Expected dividend at time of submission.",
                max_digits=16,
                null=True,
                blank=True,
            ),
        ),
        migrations.CreateModel(
            name="DividendAllocationLine",
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
                    "action_type",
                    models.CharField(
                        choices=[
                            ("cash", "Cash (MoMo / bank)"),
                            ("mcs_shares", "MCS cooperative shares (UGX 1M/share)"),
                            ("mesu_shares", "MESU Academy shares (UGX 1M/share)"),
                            ("savings", "MCS Fixed Savings (7.5% p.a.)"),
                        ],
                        max_length=20,
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=2, max_digits=16)),
                (
                    "shares_count",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Whole shares for MCS/MESU reinvestment lines.",
                    ),
                ),
                (
                    "submission",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="allocation_lines",
                        to="cooperative_shareholding.dividendchoicerequest",
                    ),
                ),
            ],
            options={
                "verbose_name": "Dividend allocation line",
                "verbose_name_plural": "Dividend allocation lines",
                "ordering": ["action_type"],
            },
        ),
        migrations.RunPython(
            migrate_legacy_dividend_choices,
            migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name="dividendchoicerequest",
            name="action_type",
        ),
        migrations.RemoveField(
            model_name="dividendchoicerequest",
            name="dividend_amount",
        ),
        migrations.RemoveField(
            model_name="dividendchoicerequest",
            name="shares_to_reinvest",
        ),
        migrations.AlterField(
            model_name="dividendchoicerequest",
            name="total_dividend",
            field=models.DecimalField(
                decimal_places=2,
                help_text="Expected dividend at time of submission.",
                max_digits=16,
            ),
        ),
        migrations.AlterModelOptions(
            name="dividendchoicerequest",
            options={
                "ordering": ["-created_at"],
                "verbose_name": "Dividend election submission",
                "verbose_name_plural": "Dividend election submissions",
            },
        ),
    ]
