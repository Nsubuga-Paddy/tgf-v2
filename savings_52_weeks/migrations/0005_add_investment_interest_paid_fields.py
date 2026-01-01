# Generated manually for interest payment tracking

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('savings_52_weeks', '0004_alter_investment_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='investment',
            name='interest_paid',
            field=models.BooleanField(default=False, help_text='Whether interest has been added to user\'s savings'),
        ),
        migrations.AddField(
            model_name='investment',
            name='interest_paid_date',
            field=models.DateField(blank=True, help_text='Date when interest was paid', null=True),
        ),
    ]

