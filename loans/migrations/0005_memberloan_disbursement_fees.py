from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("loans", "0004_alter_loanapplication_monthly_interest_rate"),
    ]

    operations = [
        migrations.AddField(
            model_name="memberloan",
            name="insurance_fee",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                max_digits=14,
            ),
        ),
        migrations.AddField(
            model_name="memberloan",
            name="processing_fee",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                max_digits=14,
            ),
        ),
        migrations.AddField(
            model_name="memberloan",
            name="total_deductions",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                max_digits=14,
            ),
        ),
        migrations.AddField(
            model_name="memberloan",
            name="net_disbursed_amount",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                max_digits=14,
            ),
        ),
    ]
