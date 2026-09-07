# Generated manually for staff announcements + member inbox

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0018_member_email_notification"),
    ]

    operations = [
        migrations.CreateModel(
            name="StaffAnnouncement",
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
                ("title", models.CharField(max_length=200)),
                (
                    "body",
                    models.TextField(
                        help_text="Plain text shown in the member inbox and email."
                    ),
                ),
                (
                    "audience",
                    models.CharField(
                        choices=[
                            ("all", "All members"),
                            ("project", "Members of a project"),
                            ("selected", "Selected members"),
                        ],
                        default="all",
                        max_length=20,
                    ),
                ),
                (
                    "send_email",
                    models.BooleanField(
                        default=True,
                        help_text="Also email recipients when this announcement is published.",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("published", "Published"),
                        ],
                        db_index=True,
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("recipient_count", models.PositiveIntegerField(default=0)),
                ("email_sent_count", models.PositiveIntegerField(default=0)),
                ("email_failed_count", models.PositiveIntegerField(default=0)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="staff_announcements_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        blank=True,
                        help_text='Required when audience is “Members of a project”.',
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="staff_announcements",
                        to="accounts.project",
                    ),
                ),
                (
                    "selected_members",
                    models.ManyToManyField(
                        blank=True,
                        help_text='Used when audience is “Selected members”.',
                        related_name="targeted_staff_announcements",
                        to="accounts.userprofile",
                    ),
                ),
            ],
            options={
                "verbose_name": "Staff announcement",
                "verbose_name_plural": "Staff announcements",
                "ordering": ["-created_at", "-pk"],
            },
        ),
        migrations.CreateModel(
            name="MemberNotification",
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
                    "source",
                    models.CharField(
                        choices=[
                            ("staff", "Staff announcement"),
                            ("system", "System"),
                        ],
                        db_index=True,
                        default="staff",
                        max_length=20,
                    ),
                ),
                ("title", models.CharField(max_length=200)),
                ("body", models.TextField()),
                ("is_read", models.BooleanField(db_index=True, default=False)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("email_sent", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "announcement",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifications",
                        to="accounts.staffannouncement",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="inbox_notifications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Member notification",
                "verbose_name_plural": "Member notifications",
                "ordering": ["-created_at", "-pk"],
            },
        ),
        migrations.AddIndex(
            model_name="membernotification",
            index=models.Index(
                fields=["user", "is_read", "-created_at"],
                name="accounts_me_user_id_7b0f0c_idx",
            ),
        ),
    ]
