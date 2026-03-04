# Generated manually for add_farm_to_cgf_action_request

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('goat_farming', '0006_add_goats_count_to_cgf_action'),
    ]

    operations = [
        migrations.AddField(
            model_name='cgfactionrequest',
            name='farm',
            field=models.ForeignKey(
                blank=True,
                help_text='Farm this action refers to (optional; if blank, totals are across all farms).',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='cgf_action_requests',
                to='goat_farming.farm',
            ),
        ),
    ]
