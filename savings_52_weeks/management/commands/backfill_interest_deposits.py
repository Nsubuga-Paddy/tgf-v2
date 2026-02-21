"""
Backfill interest deposits for all 52WSC members who participated in a given year.
Creates:
  1. Unfixed 15% interest deposits (UNFIXED-INT-{year}) for Dec 31
  2. Fixed deposit interest deposits (INT-{pk}) for matured investments

Use this to credit interest for past years so running totals and withdrawals reflect correctly.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from datetime import date

from accounts.models import UserProfile, Project
from savings_52_weeks.models import SavingsTransaction, Investment
from savings_52_weeks.interest_utils import calculate_unfixed_interest_for_year


class Command(BaseCommand):
    help = (
        'Backfill interest deposits for all 52WSC members: unfixed 15%% interest for a year, '
        'plus FD interest for matured investments. Fixes running totals and avoids negative balances.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            type=int,
            default=None,
            help='Year for unfixed interest (default: previous year)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without making changes',
        )
        parser.add_argument(
            '--unfixed-only',
            action='store_true',
            help='Only process unfixed interest (skip FD maturity)',
        )
        parser.add_argument(
            '--fd-only',
            action='store_true',
            help='Only process fixed deposit interest (skip unfixed)',
        )

    def handle(self, *args, **options):
        year = options['year']
        if year is None:
            year = timezone.now().year - 1  # Default: previous year
        dry_run = options['dry_run']
        unfixed_only = options['unfixed_only']
        fd_only = options['fd_only']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No transactions will be created'))

        self.stdout.write(f'Backfilling interest deposits for year {year}...\n')

        # ---- 1. Unfixed interest ----
        unfixed_created = 0
        if not fd_only:
            unfixed_created = self._process_unfixed_interest(year, dry_run)

        # ---- 2. Fixed deposit interest ----
        fd_created = 0
        if not unfixed_only:
            fd_created = self._process_fd_interest(dry_run)

        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(
                f'Done. Unfixed: {unfixed_created}, FD interest: {fd_created}'
                + (' (dry run - no changes)' if dry_run else '')
            )
        )

    def _process_unfixed_interest(self, year: int, dry_run: bool) -> int:
        """Create UNFIXED-INT-{year} deposits for users with unfixed interest."""
        self.stdout.write(f'--- Unfixed 15% interest for {year} ---')

        try:
            project = Project.objects.get(name='52 Weeks Saving Challenge')
            user_profiles = UserProfile.objects.filter(
                projects=project,
                is_verified=True,
            ).distinct()
        except Project.DoesNotExist:
            self.stdout.write(self.style.ERROR('52 Weeks Saving Challenge project not found.'))
            return 0

        year_end = date(year, 12, 31)
        created = 0

        for profile in user_profiles:
            existing = SavingsTransaction.objects.filter(
                user_profile=profile,
                receipt_number=f'UNFIXED-INT-{year}',
                transaction_type='deposit',
            ).exists()
            if existing:
                continue

            interest = calculate_unfixed_interest_for_year(profile, year)
            if interest <= 0:
                continue

            if dry_run:
                self.stdout.write(
                    f'  Would create: {profile.user.get_full_name() or profile.user.username} - '
                    f'UGX {interest:,.0f} (UNFIXED-INT-{year})'
                )
                created += 1
                continue

            SavingsTransaction.objects.create(
                user_profile=profile,
                amount=interest,
                transaction_type='deposit',
                transaction_date=year_end,
                receipt_number=f'UNFIXED-INT-{year}',
            )
            created += 1
            self.stdout.write(
                f'  Created: {profile.user.get_full_name() or profile.user.username} - UGX {interest:,.0f}'
            )

        self.stdout.write(f'Unfixed interest: {created} created')
        return created

    def _process_fd_interest(self, dry_run: bool) -> int:
        """Create interest deposits for all matured fixed investments."""
        self.stdout.write('--- Fixed deposit interest (matured) ---')

        fixed_investments = Investment.objects.filter(status='fixed').select_related('user_profile__user')
        matured = [inv for inv in fixed_investments if inv.is_matured]

        if not matured:
            self.stdout.write('No matured investments to process')
            return 0

        # Count how many need interest deposits (don't have INT-{pk} yet)
        to_create = []
        for inv in matured:
            existing = SavingsTransaction.objects.filter(
                user_profile=inv.user_profile,
                receipt_number=f'INT-{inv.pk}',
                transaction_type='deposit',
            ).exists()
            if existing:
                continue
            amt = inv.total_interest_expected or Decimal('0')
            if amt > 0:
                to_create.append(inv)

        if dry_run:
            for inv in to_create:
                user = inv.user_profile.user
                amt = inv.total_interest_expected or Decimal('0')
                self.stdout.write(
                    f'  Would create: {user.get_full_name() or user.username} - '
                    f'UGX {amt:,.0f} (INT-{inv.pk}, maturity {inv.maturity_date})'
                )
            self.stdout.write(f'FD interest: {len(to_create)} would be created')
            return len(to_create)

        # Process all users - check_and_update_status creates interest deposits for matured FDs
        matured_investments = Investment.check_all_investments_status()
        for inv in matured_investments:
            user = inv.user_profile.user
            amt = inv.total_interest_expected or Decimal('0')
            self.stdout.write(
                f'  Created: {user.get_full_name() or user.username} - UGX {amt:,.0f} '
                f'(maturity {inv.maturity_date})'
            )
        self.stdout.write(f'FD interest: {len(matured_investments)} created')
        return len(matured_investments)
