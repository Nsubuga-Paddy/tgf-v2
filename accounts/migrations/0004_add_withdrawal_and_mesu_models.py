# Generated manually for WithdrawalRequest and MESUInterest models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_add_bank_account_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='WithdrawalRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, help_text='Amount to withdraw', max_digits=14)),
                ('status', models.CharField(choices=[('pending', 'Pending Approval'), ('approved', 'Approved - Transfer Confirmed'), ('rejected', 'Rejected'), ('completed', 'Completed - Amount Deducted')], default='pending', help_text='Request status', max_length=20)),
                ('bank_name', models.CharField(help_text='Bank name', max_length=100)),
                ('bank_account_number', models.CharField(help_text='Account number', max_length=50)),
                ('bank_account_name', models.CharField(help_text='Account name', max_length=200)),
                ('admin_notes', models.TextField(blank=True, help_text='Admin notes about this withdrawal')),
                ('requested_at', models.DateTimeField(auto_now_add=True)),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('approved_by', models.ForeignKey(blank=True, help_text='Admin who approved this withdrawal', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_withdrawals', to=settings.AUTH_USER_MODEL)),
                ('user_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='withdrawal_requests', to='accounts.userprofile')),
            ],
            options={
                'verbose_name': 'Withdrawal Request',
                'verbose_name_plural': 'Withdrawal Requests',
                'ordering': ['-requested_at'],
            },
        ),
        migrations.CreateModel(
            name='MESUInterest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('shares_requested', models.PositiveIntegerField(help_text='Number of shares requested (1 share = 1M)')),
                ('total_amount', models.DecimalField(decimal_places=2, help_text='Total amount (shares × 1,000,000)', max_digits=14)),
                ('status', models.CharField(choices=[('pending', 'Pending Approval'), ('approved', 'Approved - Processing'), ('rejected', 'Rejected'), ('completed', 'Completed - Shares Purchased')], default='pending', help_text='Request status', max_length=20)),
                ('admin_notes', models.TextField(blank=True, help_text='Admin notes about this request')),
                ('requested_at', models.DateTimeField(auto_now_add=True)),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('approved_by', models.ForeignKey(blank=True, help_text='Admin who approved this request', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_mesu_interests', to=settings.AUTH_USER_MODEL)),
                ('user_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mesu_interests', to='accounts.userprofile')),
            ],
            options={
                'verbose_name': 'MESU Interest',
                'verbose_name_plural': 'MESU Interests',
                'ordering': ['-requested_at'],
            },
        ),
    ]

