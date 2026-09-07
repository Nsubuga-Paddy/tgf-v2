# Generated manually for Main Account share purchases

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main_account", "0007_alter_mainaccounttransaction_category"),
    ]

    operations = [
        migrations.AlterField(
            model_name="mainaccounttransaction",
            name="category",
            field=models.CharField(
                choices=[
                    ("opening_balance", "Opening balance"),
                    ("admin_credit", "Admin credit"),
                    ("project_transfer_in", "Transfer from project"),
                    ("dividend", "Dividend payout"),
                    ("loan_disbursement", "Loan disbursement"),
                    ("project_investment", "Investment into project"),
                    ("loan_repayment", "Loan repayment"),
                    ("share_purchase", "Share purchase"),
                    ("withdrawal", "Withdrawal to bank"),
                    ("adjustment", "Adjustment / correction"),
                ],
                max_length=30,
            ),
        ),
    ]
