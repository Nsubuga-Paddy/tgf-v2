import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


def seed_deposit_funded_activities(apps, schema_editor):
    GWCFixedDeposit = apps.get_model("gwc", "GWCFixedDeposit")
    GWCDepositActivity = apps.get_model("gwc", "GWCDepositActivity")
    for d in GWCFixedDeposit.objects.all():
        if not GWCDepositActivity.objects.filter(
            deposit_id=d.pk, description="Deposit funded"
        ).exists():
            GWCDepositActivity.objects.create(
                deposit_id=d.pk,
                description="Deposit funded",
                activity_type="credit",
                amount=d.principal_amount,
                timestamp=d.created_at,
            )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("gwc", "0002_simplify_gwc_remove_activity"),
    ]

    operations = [
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
        migrations.RunPython(seed_deposit_funded_activities, noop_reverse),
    ]
