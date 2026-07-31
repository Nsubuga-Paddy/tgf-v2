from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main_account", "0002_admin_main_account_credit_proxy"),
    ]

    operations = [
        migrations.AddField(
            model_name="mainaccountwithdrawal",
            name="payout_destination",
            field=models.CharField(
                blank=True,
                help_text="Snapshot of mobile number or bank details at request time.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="mainaccountwithdrawal",
            name="payout_method",
            field=models.CharField(
                choices=[("mobile_money", "Mobile money"), ("bank", "Bank account")],
                default="bank",
                help_text="Where the member asked funds to be sent.",
                max_length=20,
            ),
        ),
    ]
