# Generated manually for GWC monthly interest redemption

from decimal import Decimal

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("main_account", "0006_withdrawal_funding_note"),
        ("gwc", "0004_alter_gwcdepositactivity_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="gwcfixeddeposit",
            name="redeemable_monthly_interest",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text=(
                    "When enabled, the member may transfer calendar-month interest "
                    "(net of tax) to their Main Account before maturity. Typical for "
                    "large single deposits (e.g. group ~120M). Leave off for lock-to-maturity "
                    "deposits (e.g. individual ~12M)."
                ),
            ),
        ),
        migrations.CreateModel(
            name="GWCInterestRedemption",
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
                ("amount", models.DecimalField(decimal_places=2, max_digits=16)),
                (
                    "redeemed_at",
                    models.DateTimeField(
                        db_index=True, default=django.utils.timezone.now
                    ),
                ),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="gwc_interest_redemptions_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "deposit",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="interest_redemptions",
                        to="gwc.gwcfixeddeposit",
                    ),
                ),
                (
                    "main_account_transaction",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="gwc_interest_redemptions",
                        to="main_account.mainaccounttransaction",
                    ),
                ),
            ],
            options={
                "verbose_name": "GWC interest redemption",
                "verbose_name_plural": "GWC interest redemptions",
                "ordering": ["-redeemed_at", "-pk"],
            },
        ),
    ]
