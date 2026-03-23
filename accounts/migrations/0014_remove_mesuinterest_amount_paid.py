# Undo MESU partial-payment field (revert shareholding feature)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0013_mesuinterest_amount_paid"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="mesuinterest",
            name="amount_paid",
        ),
    ]
