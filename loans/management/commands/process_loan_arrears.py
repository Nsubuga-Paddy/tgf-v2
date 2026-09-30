from django.core.management.base import BaseCommand

from loans.operations import process_loan_arrears


class Command(BaseCommand):
    help = (
        "Refresh overdue loan statuses, accrue continuing interest after the agreed term, "
        "attempt Main Account auto-debits, notify members, and send the monthly staff digest. "
        "In production, run via: python manage.py run_daily_jobs"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Count open loans without posting charges, emails, or auto-debits.",
        )

    def handle(self, *args, **options):
        if options["dry_run"]:
            from loans.models import MemberLoan

            count = MemberLoan.objects.filter(status__in=["active", "overdue"]).count()
            overdue = MemberLoan.objects.filter(status="overdue").count()
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: {count} open loan(s), {overdue} currently marked overdue. No changes made."
                )
            )
            return

        stats = process_loan_arrears()
        self.stdout.write(
            self.style.SUCCESS(
                "Processed {loans} open loan(s): {charges} interest accrual(s), "
                "{first_notices} first overdue notice(s), {monthly_reminders} monthly reminder(s), "
                "{auto_debit_paid} auto-debit(s) paid, {auto_debit_failed} auto-debit failure(s), "
                "staff digest {digest}.".format(
                    digest="sent" if stats["staff_digest"] else "not sent",
                    **stats,
                )
            )
        )
