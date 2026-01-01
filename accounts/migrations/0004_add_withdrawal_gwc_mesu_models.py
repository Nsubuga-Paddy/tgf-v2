# Generated manually for adding withdrawal, GWC, and MESU models

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_add_bank_account_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='WithdrawalRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, help_text='Withdrawal amount in UGX', max_digits=12)),
                ('reason', models.TextField(blank=True, help_text='Reason for withdrawal', null=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('processed', 'Processed')], default='pending', max_length=20)),
                ('admin_notes', models.TextField(blank=True, help_text='Admin notes', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('user_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='withdrawal_requests', to='accounts.userprofile')),
            ],
            options={
                'verbose_name': 'Withdrawal Request',
                'verbose_name_plural': 'Withdrawal Requests',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='MESUInterest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('investment_amount', models.DecimalField(decimal_places=2, help_text='Investment amount in UGX', max_digits=12)),
                ('number_of_shares', models.PositiveIntegerField(default=0, help_text='Number of shares (calculated: 1 share = UGX 1,000,000)')),
                ('notes', models.TextField(blank=True, help_text='Additional notes from user', null=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('processed', 'Processed')], default='pending', max_length=20)),
                ('admin_notes', models.TextField(blank=True, help_text='Admin notes', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('user_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mesu_interests', to='accounts.userprofile')),
            ],
            options={
                'verbose_name': 'MESU Interest',
                'verbose_name_plural': 'MESU Interests',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='GWCContribution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, help_text='Contribution amount in UGX', max_digits=12)),
                ('group_type', models.CharField(choices=[('individual', 'Individual Contribution'), ('group', 'Group Contribution')], help_text='Type of contribution', max_length=20)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('processed', 'Processed')], default='pending', max_length=20)),
                ('admin_notes', models.TextField(blank=True, help_text='Admin notes', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('user_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='gwc_contributions', to='accounts.userprofile')),
            ],
            options={
                'verbose_name': 'GWC Contribution',
                'verbose_name_plural': 'GWC Contributions',
                'ordering': ['-created_at'],
            },
        ),
    ]

