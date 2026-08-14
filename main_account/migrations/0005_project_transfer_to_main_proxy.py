from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("main_account", "0004_mainaccountwithdrawal_reversal_transaction_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProjectTransferToMainAccount",
            fields=[],
            options={
                "verbose_name": "Project transfer to main account",
                "verbose_name_plural": "Project transfers to main account",
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("main_account.mainaccounttransaction",),
        ),
        migrations.AlterModelOptions(
            name="projecttransferrequest",
            options={
                "ordering": ["-created_at"],
                "verbose_name": "Legacy project transfer request",
                "verbose_name_plural": "Legacy project transfer requests",
            },
        ),
    ]
