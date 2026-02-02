"""
Accrue 15% annualized interest on unfixed savings for a calendar year.
Creates one deposit transaction per user on Dec 31, adding to running deposit and transaction history.
Run annually (e.g. via cron on Jan 1 for the previous year, or on Dec 31 for that year).
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from datetime import date

from accounts.models import UserProfile, Project
from savings_52_weeks.models import SavingsTransaction
from savings_52_weeks.interest_utils import (
    calculate_unfixed_interest_for_year,
    calculate_unfixed_interest_for_period,
)


class Command(BaseCommand):
    help = (
        'Accrue annual 15%% interest on unfixed savings. Creates one deposit per user '
        'on Dec 31 for the specified year. Interest is added to running deposit and transaction history.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            type=int,
            default=None,
            help='Year to accrue interest for (default: current year)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without making changes',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Allow running for current year before Dec 31 (credits partial year only)',
        )

    def handle(self, *args, **options):
        year = options['year'] or timezone.now().year
        dry_run = options['dry_run']
        today = timezone.localdate()
        force = options.get('force', False)
        year_end = date(year, 12, 31)

        # For current year before Dec 31, require --force (partial year) or refuse
        if year == today.year and today < year_end:
            if not force and not dry_run:
                self.stdout.write(
                    self.style.ERROR(
                        f'Cannot accrue for {year} before Dec 31. '
                        'Run after Dec 31 for full year, or use --force for partial year, or --dry-run to preview.'
                    )
                )
                return
            target_date = today  # Partial year: credit as of today
            if not dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f'Running for partial year: Jan 1 - {today} (use only for testing/catch-up)'
                    )
                )
        else:
            target_date = year_end  # Full year: credit on Dec 31

        if dry_run:
            self.stdout.write(self.style.WARNING(f'DRY RUN - No transactions will be created for year {year}'))

        # Get 52WSC users
        try:
            project = Project.objects.get(name='52 Weeks Saving Challenge')
            user_profiles = UserProfile.objects.filter(
                projects=project,
                is_verified=True,
            ).distinct()
        except Project.DoesNotExist:
            self.stdout.write(self.style.ERROR('52 Weeks Saving Challenge project not found.'))
            return

        self.stdout.write(f'Processing {user_profiles.count()} users for year {year}...')

        created = 0
        skipped = 0
        zero_interest = 0

        for profile in user_profiles:
            # Check if already processed
            existing = SavingsTransaction.objects.filter(
                user_profile=profile,
                receipt_number=f'UNFIXED-INT-{year}',
                transaction_type='deposit',
            ).exists()

            if existing:
                skipped += 1
                self.stdout.write(f'  Skip {profile}: already has UNFIXED-INT-{year}')
                continue

            if target_date == year_end:
                interest = calculate_unfixed_interest_for_year(profile, year)
            else:
                interest = calculate_unfixed_interest_for_period(
                    profile, date(year, 1, 1), target_date
                )

            if interest <= 0:
                zero_interest += 1
                continue

            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  Would create: {profile.user.get_full_name() or profile.user.username} - '
                        f'UGX {interest:,.0f} (UNFIXED-INT-{year})'
                    )
                )
                created += 1
                continue

            SavingsTransaction.objects.create(
                user_profile=profile,
                amount=interest,
                transaction_type='deposit',
                transaction_date=target_date,
                receipt_number=f'UNFIXED-INT-{year}',
            )
            created += 1
            self.stdout.write(
                f'  Created: {profile.user.get_full_name() or profile.user.username} - UGX {interest:,.0f}'
            )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Done. Created: {created}, Skipped (already exists): {skipped}, Zero interest: {zero_interest}'))
