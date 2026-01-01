# Generated manually for GeneralAccount models

from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_add_withdrawal_and_mesu_models'),
    ]

    operations = [
        migrations.CreateModel(
            name='GeneralAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('balance', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Current balance in general account', max_digits=14)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user_profile', models.OneToOneField(help_text="User's general account", on_delete=django.db.models.deletion.CASCADE, related_name='general_account', to='accounts.userprofile')),
            ],
            options={
                'verbose_name': 'General Account',
                'verbose_name_plural': 'General Accounts',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='GeneralAccountTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, help_text='Transaction amount', max_digits=14)),
                ('transaction_type', models.CharField(choices=[('deposit', 'Deposit'), ('withdrawal', 'Withdrawal'), ('transfer_in', 'Transfer In'), ('transfer_out', 'Transfer Out')], help_text='Type of transaction', max_length=20)),
                ('description', models.TextField(blank=True, help_text='Transaction description')),
                ('receipt_number', models.CharField(blank=True, help_text='Receipt or reference number', max_length=100, null=True)),
                ('source_project', models.CharField(blank=True, help_text="Source project name (e.g., '52 Weeks Saving Challenge 2025')", max_length=200, null=True)),
                ('transaction_date', models.DateField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('general_account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='accounts.generalaccount')),
            ],
            options={
                'verbose_name': 'General Account Transaction',
                'verbose_name_plural': 'General Account Transactions',
                'ordering': ['-created_at'],
            },
        ),
    ]

