# Migration to remove GeneralAccount and GeneralAccountTransaction models

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_create_general_accounts_for_existing_users'),
    ]

    operations = [
        migrations.DeleteModel(
            name='GeneralAccountTransaction',
        ),
        migrations.DeleteModel(
            name='GeneralAccount',
        ),
    ]

