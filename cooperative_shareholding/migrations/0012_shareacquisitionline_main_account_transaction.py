from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("cooperative_shareholding", "0011_dividend_main_account_claim"),
        ("main_account", "0008_alter_mainaccounttransaction_category"),
    ]

    operations = [
        migrations.AddField(
            model_name="shareacquisitionline",
            name="main_account_transaction",
            field=models.OneToOneField(
                blank=True,
                help_text="Main Account debit that funded this member purchase, when applicable.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="share_acquisition",
                to="main_account.mainaccounttransaction",
            ),
        ),
    ]
