# Generated manually for adding withdrawal and GWC contribution links

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('savings_52_weeks', '0004_alter_investment_status'),
        ('accounts', '0004_add_withdrawal_gwc_mesu_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='savingstransaction',
            name='gwc_contribution',
            field=models.ForeignKey(
                blank=True,
                help_text='Linked GWC contribution (if this transaction is from a GWC contribution)',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='savings_transactions',
                to='accounts.gwccontribution'
            ),
        ),
        migrations.AddField(
            model_name='savingstransaction',
            name='withdrawal_request',
            field=models.ForeignKey(
                blank=True,
                help_text='Linked withdrawal request (if this transaction is from a withdrawal)',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='savings_transactions',
                to='accounts.withdrawalrequest'
            ),
        ),
        migrations.AlterField(
            model_name='savingstransaction',
            name='transaction_type',
            field=models.CharField(
                choices=[
                    ('deposit', 'Deposit'),
                    ('withdrawal', 'Withdrawal'),
                    ('adjustment', 'Adjustment'),
                    ('gwc_contribution', 'GWC Contribution')
                ],
                default='deposit',
                help_text='Type of transaction',
                max_length=20
            ),
        ),
    ]
