# Generated manually for MESU partial payments

from decimal import Decimal

from django.db import migrations, models
from django.db.models import F


def backfill_amount_paid(apps, schema_editor):
    MESUInterest = apps.get_model("accounts", "MESUInterest")
    MESUInterest.objects.filter(status__in=["approved", "processed"]).update(
        amount_paid=F("investment_amount")
    )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0012_drop_extra_columns"),
    ]

    operations = [
        migrations.AddField(
            model_name="mesuinterest",
            name="amount_paid",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0"),
                help_text="Amount received toward this request (UGX). Use for installment / partial payments.",
                max_digits=12,
            ),
        ),
        migrations.RunPython(backfill_amount_paid, migrations.RunPython.noop),
    ]
