from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cooperative_shareholding", "0004_rename_dividend_submission_verbose_names"),
    ]

    operations = [
        migrations.AddField(
            model_name="shareacquisitionline",
            name="source_description",
            field=models.CharField(
                blank=True,
                help_text="e.g. dividend reinvestment choice, manual purchase.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="dividendchoicerequest",
            name="ledger_applied_at",
            field=models.DateTimeField(
                blank=True,
                help_text="When approved allocations were posted to acquisitions / related ledgers.",
                null=True,
            ),
        ),
    ]
