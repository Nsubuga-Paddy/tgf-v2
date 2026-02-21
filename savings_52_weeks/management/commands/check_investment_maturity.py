from django.core.management.base import BaseCommand
from django.utils import timezone
from savings_52_weeks.models import Investment


class Command(BaseCommand):
    help = (
        'Check and update maturity status for all investments. '
        'Upon maturity, creates interest deposit transactions and updates status.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))

        # Get all fixed investments that have matured
        fixed_investments = Investment.objects.filter(status='fixed').select_related('user_profile__user')
        matured_investments = [inv for inv in fixed_investments if inv.is_matured]

        self.stdout.write(f"Found {len(matured_investments)} matured investments (of {fixed_investments.count()} fixed)")

        if not matured_investments:
            self.stdout.write(self.style.SUCCESS("No investments have matured yet"))

            total_fixed = Investment.objects.filter(status='fixed').count()
            total_matured = Investment.objects.filter(status='matured').count()
            self.stdout.write(f"\nSummary:")
            self.stdout.write(f"  Fixed investments: {total_fixed}")
            self.stdout.write(f"  Matured investments: {total_matured}")
            return

        updated = 0
        for investment in matured_investments:
            user = investment.user_profile.user
            if dry_run:
                self.stdout.write(
                    f"  Would process: {user.get_full_name() or user.username} - "
                    f"UGX {investment.amount_invested:,.0f} matured on {investment.maturity_date} "
                    f"(would create interest deposit INT-{investment.pk})"
                )
                updated += 1
            else:
                if investment.check_and_update_status():
                    updated += 1
                    self.stdout.write(
                        f"  Processed: {user.get_full_name() or user.username} - "
                        f"UGX {investment.amount_invested:,.0f} matured on {investment.maturity_date}"
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n{'Would update' if dry_run else 'Updated'} {updated} investments "
                f"(status + interest deposit transactions)"
            )
        )

        # Show summary
        total_fixed = Investment.objects.filter(status='fixed').count()
        total_matured = Investment.objects.filter(status='matured').count()
        self.stdout.write(f"\nSummary:")
        self.stdout.write(f"  Fixed investments: {total_fixed}")
        self.stdout.write(f"  Matured investments: {total_matured}")
