# Generated manually for cooperative shareholding refactor

from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion


def migrate_settings_forward(apps, schema_editor):
    OldSettings = apps.get_model("cooperative_shareholding", "CooperativeSettings")
    GlobalDefaults = apps.get_model("cooperative_shareholding", "CooperativeGlobalDefaults")
    Shareholding = apps.get_model("cooperative_shareholding", "CooperativeShareholding")

    old = OldSettings.objects.filter(pk=1).first()
    reinvest = Decimal("1000000")
    blue = Decimal("1000000")
    share_price = Decimal("100000")
    div_rate = Decimal("0.26")
    election_open = False
    usd_rate = Decimal("3800")

    if old:
        reinvest = old.reinvest_share_price
        blue = old.blue_diamond_usd_threshold
        share_price = old.current_share_price
        div_rate = old.dividend_rate
        election_open = old.dividend_election_open
        usd_rate = old.usd_to_ugx_rate

    GlobalDefaults.objects.get_or_create(
        pk=1,
        defaults={
            "reinvest_share_price": reinvest,
            "blue_diamond_usd_threshold": blue,
        },
    )

    IssuancePeriod = apps.get_model(
        "cooperative_shareholding", "CooperativeIssuancePeriod"
    )
    period, _ = IssuancePeriod.objects.get_or_create(
        name="Default issuance",
        defaults={"usd_to_ugx_rate": usd_rate},
    )

    for sh in Shareholding.objects.all():
        sh.current_share_price = share_price
        sh.dividend_rate = div_rate
        sh.dividend_election_open = election_open
        sh.issuance_period = period
        sh.save(
            update_fields=[
                "current_share_price",
                "dividend_rate",
                "dividend_election_open",
                "issuance_period",
            ]
        )


class Migration(migrations.Migration):

    dependencies = [
        ("cooperative_shareholding", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CooperativeGlobalDefaults",
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
                    "reinvest_share_price",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("1000000"),
                        max_digits=14,
                    ),
                ),
                (
                    "blue_diamond_usd_threshold",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("1000000"),
                        max_digits=14,
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Cooperative global defaults",
                "verbose_name_plural": "Cooperative global defaults",
            },
        ),
        migrations.CreateModel(
            name="CooperativeIssuancePeriod",
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
                ("name", models.CharField(max_length=120)),
                (
                    "usd_to_ugx_rate",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("3800"),
                        max_digits=14,
                    ),
                ),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Issuance period (USD rate)",
                "verbose_name_plural": "Issuance periods (USD rates)",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddField(
            model_name="cooperativeshareholding",
            name="current_share_price",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("100000"),
                max_digits=14,
            ),
        ),
        migrations.AddField(
            model_name="cooperativeshareholding",
            name="dividend_rate",
            field=models.DecimalField(
                decimal_places=4,
                default=Decimal("0.26"),
                max_digits=7,
            ),
        ),
        migrations.AddField(
            model_name="cooperativeshareholding",
            name="dividend_election_open",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="cooperativeshareholding",
            name="issuance_period",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="shareholdings",
                to="cooperative_shareholding.cooperativeissuanceperiod",
            ),
        ),
        migrations.RunPython(migrate_settings_forward, migrations.RunPython.noop),
        migrations.DeleteModel(
            name="CooperativeSettings",
        ),
    ]
