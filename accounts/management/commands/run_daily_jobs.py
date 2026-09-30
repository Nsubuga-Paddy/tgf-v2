"""
Run every MCS job that should fire once per day.

Railway cron (one call):

  python manage.py run_daily_jobs

Order:
  1. 52WSC fixed-deposit maturity
  2. Birthday / matured-project / GWC interest emails
  3. Loan arrears, auto-debit, and staff digest
  4. Unfixed 52WSC annual interest — only on 31 Dec or 1 Jan
"""
from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone


DAILY_JOBS = (
    ("check_investment_maturity", "52WSC fixed-deposit maturity"),
    ("notify_member_milestones", "Birthday and matured-project emails"),
    ("process_loan_arrears", "Loan arrears, auto-debit, staff digest"),
)


class Command(BaseCommand):
    help = (
        "Run all daily MCS jobs in one call. Point the Railway cron at this command."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Pass --dry-run through to each job. No emails, charges, or ledger writes.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options["dry_run"])
        today = timezone.localdate()
        kwargs = {"dry_run": True} if dry_run else {}
        failures = []

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - forwarding --dry-run to each job"))

        self.stdout.write(f"Daily jobs for {today.isoformat()}")
        self.stdout.write("")

        for command_name, label in DAILY_JOBS:
            self.stdout.write(self.style.MIGRATE_HEADING(f"== {label} ({command_name}) =="))
            try:
                call_command(command_name, **kwargs)
            except Exception as exc:
                failures.append(command_name)
                self.stderr.write(self.style.ERROR(f"{command_name} failed: {exc}"))
            self.stdout.write("")

        if today.month == 12 and today.day == 31:
            year = today.year
            self.stdout.write(
                self.style.MIGRATE_HEADING(f"== Unfixed 52WSC annual interest ({year}) ==")
            )
            try:
                call_command("accrue_annual_unfixed_interest", year=year, **kwargs)
            except Exception as exc:
                failures.append("accrue_annual_unfixed_interest")
                self.stderr.write(self.style.ERROR(f"accrue_annual_unfixed_interest failed: {exc}"))
            self.stdout.write("")
        elif today.month == 1 and today.day == 1:
            year = today.year - 1
            self.stdout.write(
                self.style.MIGRATE_HEADING(f"== Unfixed 52WSC annual interest ({year}) ==")
            )
            try:
                call_command("accrue_annual_unfixed_interest", year=year, **kwargs)
            except Exception as exc:
                failures.append("accrue_annual_unfixed_interest")
                self.stderr.write(self.style.ERROR(f"accrue_annual_unfixed_interest failed: {exc}"))
            self.stdout.write("")

        if failures:
            raise SystemExit(
                f"Daily jobs finished with {len(failures)} failure(s): {', '.join(failures)}"
            )

        self.stdout.write(self.style.SUCCESS("All daily jobs finished."))
