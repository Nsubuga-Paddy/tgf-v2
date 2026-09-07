"""
Send birthday celebration emails and matured / redeemable-interest digests.

Schedule daily (Railway cron, GitHub Action, or Windows Task Scheduler), e.g.:

  python manage.py notify_member_milestones

Options:
  --dry-run          Print what would be sent; do not email or write the dedupe log
  --birthdays-only   Only birthday emails
  --maturity-only    Only matured / redeemable digests
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.milestone_emails import run_member_milestone_notifications


class Command(BaseCommand):
    help = (
        "Email members about birthdays and matured / redeemable project funds "
        "(CGF, 52WSC, GWC monthly interest)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show counts without sending email or writing notification logs.",
        )
        parser.add_argument(
            "--birthdays-only",
            action="store_true",
            help="Only process birthday celebration emails.",
        )
        parser.add_argument(
            "--maturity-only",
            action="store_true",
            help="Only process matured / redeemable digests.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options["dry_run"])
        birthdays_only = bool(options["birthdays_only"])
        maturity_only = bool(options["maturity_only"])
        if birthdays_only and maturity_only:
            self.stderr.write(
                self.style.ERROR("Use only one of --birthdays-only or --maturity-only.")
            )
            return

        birthdays = not maturity_only
        maturity = not birthdays_only
        as_of = timezone.localdate()

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no emails will be sent"))

        self.stdout.write(f"Running member milestone notifications for {as_of.isoformat()}…")
        stats = run_member_milestone_notifications(
            as_of=as_of,
            dry_run=dry_run,
            birthdays=birthdays,
            maturity=maturity,
        )

        self.stdout.write("")
        self.stdout.write("Birthday emails")
        self.stdout.write(f"  sent/dry-run: {stats['birthday_sent']}")
        self.stdout.write(f"  skipped (already sent): {stats['birthday_skipped']}")
        self.stdout.write(f"  no email on file: {stats['birthday_no_email']}")
        self.stdout.write(f"  failed: {stats['birthday_failed']}")

        self.stdout.write("")
        self.stdout.write("Matured / redeemable digests")
        self.stdout.write(f"  candidates with items: {stats['maturity_candidates']}")
        self.stdout.write(f"  sent/dry-run: {stats['maturity_sent']}")
        self.stdout.write(f"  skipped (already sent): {stats['maturity_skipped']}")
        self.stdout.write(f"  no email on file: {stats['maturity_no_email']}")
        self.stdout.write(f"  failed: {stats['maturity_failed']}")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Done."))
        if not dry_run:
            self.stdout.write(
                "Schedule this command daily in production so members are notified "
                "when projects mature or GWC interest becomes redeemable, and on their birthday."
            )
