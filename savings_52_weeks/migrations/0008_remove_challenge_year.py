# Migration to remove challenge_year field from SavingsTransaction

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('savings_52_weeks', '0007_backfill_challenge_year'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='savingstransaction',
            name='challenge_year',
        ),
    ]

