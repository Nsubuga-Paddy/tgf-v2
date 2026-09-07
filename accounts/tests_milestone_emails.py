from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.milestone_emails import (
    maturity_digest_key,
    send_birthday_email,
    send_maturity_digest_email,
)
from accounts.models import MemberEmailNotification, UserProfile

User = get_user_model()


class MilestoneEmailTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="mile_t1",
            password="x",
            email="member@example.com",
            first_name="Amina",
        )
        # Profile may be auto-created by signal; ensure birthdate.
        profile, _ = UserProfile.objects.get_or_create(user=self.user)
        profile.birthdate = date(1990, timezone.localdate().month, timezone.localdate().day)
        profile.account_number = "MCSTGF-AB1234"
        profile.save(update_fields=["birthdate", "account_number"])

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_birthday_email_once_per_year(self):
        from django.core import mail

        status = send_birthday_email(self.user)
        self.assertEqual(status, "sent")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Happy Birthday", mail.outbox[0].subject)
        self.assertIn("Amina", mail.outbox[0].body)
        self.assertIn("Thank you for saving and investing", mail.outbox[0].body)
        self.assertIn("/login", mail.outbox[0].body)

        status2 = send_birthday_email(self.user)
        self.assertEqual(status2, "skipped")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            MemberEmailNotification.objects.filter(
                user=self.user,
                event_type=MemberEmailNotification.EventType.BIRTHDAY,
            ).count(),
            1,
        )

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_maturity_digest_content_and_dedupe(self):
        from django.core import mail

        items = [
            {
                "code": "gwc",
                "title": "Generational Wealth Creation",
                "amount": Decimal("2500000"),
                "amount_label": "UGX 2,500,000",
                "detail": "1 deposit with redeemable monthly interest",
                "actions": [
                    "Open Matured projects or your GWC page",
                    "Redeem full or partial interest to Main Account",
                ],
                "fingerprint": "gwc:GWC-2026-00001:2500000",
            }
        ]
        status = send_maturity_digest_email(self.user, items)
        self.assertEqual(status, "sent")
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        self.assertIn("Thank you for saving and investing", body)
        self.assertIn("UGX 2,500,000", body)
        self.assertIn("Redeem full or partial", body)
        self.assertIn("/login", body)

        status2 = send_maturity_digest_email(self.user, items)
        self.assertEqual(status2, "skipped")
        self.assertEqual(len(mail.outbox), 1)

        # New fingerprint → new email
        items[0]["fingerprint"] = "gwc:GWC-2026-00001:3000000"
        items[0]["amount_label"] = "UGX 3,000,000"
        status3 = send_maturity_digest_email(self.user, items)
        self.assertEqual(status3, "sent")
        self.assertEqual(len(mail.outbox), 2)
        self.assertNotEqual(
            maturity_digest_key(items),
            "digest:",
        )
