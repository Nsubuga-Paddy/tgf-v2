# Generated manually for adding bank account fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_alter_project_options_alter_userprofile_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='bank_name',
            field=models.CharField(blank=True, help_text='Name of the bank (e.g., Centenary Bank, Stanbic Bank)', max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='bank_account_number',
            field=models.CharField(blank=True, help_text='Bank account number', max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='bank_account_name',
            field=models.CharField(blank=True, help_text='Name as it appears on the bank account', max_length=200, null=True),
        ),
    ]

