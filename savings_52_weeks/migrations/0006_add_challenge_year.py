# Generated manually for challenge_year field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('savings_52_weeks', '0005_add_investment_interest_paid_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='savingstransaction',
            name='challenge_year',
            field=models.PositiveIntegerField(blank=True, help_text='Year of the 52-week challenge this transaction belongs to (e.g., 2025, 2026)', null=True),
        ),
    ]

