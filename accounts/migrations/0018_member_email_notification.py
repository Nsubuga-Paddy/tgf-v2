# Generated manually for member milestone emails

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0017_legacy_52wsc_withdrawal_verbose"),
    ]

    operations = [
        migrations.CreateModel(
            name="MemberEmailNotification",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "event_type",
                    models.CharField(
                        choices=[
                            ("birthday", "Birthday celebration"),
                            ("maturity_digest", "Matured / redeemable digest"),
                        ],
                        db_index=True,
                        max_length=40,
                    ),
                ),
                (
                    "event_key",
                    models.CharField(
                        db_index=True,
                        help_text="Stable id for dedupe, e.g. birthday:2026 or digest fingerprint.",
                        max_length=191,
                    ),
                ),
                ("subject", models.CharField(blank=True, max_length=255)),
                ("meta", models.JSONField(blank=True, default=dict)),
                (
                    "sent_at",
                    models.DateTimeField(
                        db_index=True, default=django.utils.timezone.now
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="member_email_notifications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Member email notification",
                "verbose_name_plural": "Member email notifications",
                "ordering": ["-sent_at", "-pk"],
            },
        ),
        migrations.AddConstraint(
            model_name="memberemailnotification",
            constraint=models.UniqueConstraint(
                fields=("user", "event_type", "event_key"),
                name="uniq_member_email_notification",
            ),
        ),
    ]
