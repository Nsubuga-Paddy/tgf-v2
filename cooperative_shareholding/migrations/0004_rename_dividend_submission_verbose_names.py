from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("cooperative_shareholding", "0003_dividend_split_allocations"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="dividendchoicerequest",
            options={
                "ordering": ["-created_at"],
                "verbose_name": "Dividend request submission",
                "verbose_name_plural": "Dividend request submissions",
            },
        ),
    ]
