from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0020_rename_accounts_me_user_id_7b0f0c_idx_accounts_me_user_id_26ff08_idx"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="is_mcs_staff",
            field=models.BooleanField(
                default=False,
                help_text="MCS staff member. Staff loans use 1% monthly interest; shareholding remains a soft review factor.",
            ),
        ),
    ]
