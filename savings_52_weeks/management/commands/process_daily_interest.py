"""
Daily management command to process:
1. Matured investment interest payments
2. Uninvested savings interest on Dec 31, 2025
3. Transfer all 52WSC 2025 savings to accounts on Jan 1, 2026
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction as db_transaction
from decimal import Decimal
from datetime import date
from savings_52_weeks.models import Investment, SavingsTransaction
from accounts.models import UserProfile


class Command(BaseCommand):
    help = 'Process matured investment interest, uninvested savings interest, and end-of-challenge transfers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        today = timezone.localdate()
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        self.stdout.write(f"Processing for date: {today}")
        
        # 1. Process matured investments
        self.process_matured_investments(dry_run)
        
        # 2. Process uninvested savings interest on Dec 31, 2025
        if today == date(2025, 12, 31):
            self.process_uninvested_savings_interest(dry_run)
        
        # 3. Transfer all savings to accounts on Jan 1, 2026
        if today == date(2026, 1, 1):
            self.transfer_challenge_savings(dry_run)
        
        self.stdout.write(self.style.SUCCESS('Daily processing completed'))

    def process_matured_investments(self, dry_run=False):
        """Process interest for all matured investments that haven't been paid yet"""
        self.stdout.write("\n=== Processing Matured Investments ===")
        
        # Get all matured investments that haven't been paid
        matured_investments = Investment.objects.filter(
            status='matured',
            interest_paid=False
        )
        
        count = matured_investments.count()
        self.stdout.write(f"Found {count} matured investments to process")
        
        if count == 0:
            return
        
        processed_count = 0
        total_interest = Decimal('0.00')
        
        for investment in matured_investments:
            # Double-check maturity
            if investment.maturity_date > timezone.localdate():
                continue
            
            interest_amount = investment.total_interest_expected
            
            if dry_run:
                self.stdout.write(
                    f"  [DRY RUN] Would process: {investment.user_profile.user.get_username()} - "
                    f"Investment #{investment.id} - Interest: UGX {interest_amount:,.0f}"
                )
            else:
                try:
                    with db_transaction.atomic():
                        transaction = investment.process_maturity_interest()
                        if transaction:
                            processed_count += 1
                            total_interest += interest_amount
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"  ✓ Processed: {investment.user_profile.user.get_username()} - "
                                    f"Investment #{investment.id} - Interest: UGX {interest_amount:,.0f}"
                                )
                            )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"  ✗ Error processing investment #{investment.id}: {str(e)}"
                        )
                    )
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nProcessed {processed_count} investments. Total interest paid: UGX {total_interest:,.0f}"
                )
            )

    def process_uninvested_savings_interest(self, dry_run=False):
        """Process 15% interest on uninvested savings for all users on Dec 31, 2025"""
        self.stdout.write("\n=== Processing Uninvested Savings Interest (Dec 31, 2025) ===")
        
        # Get all users with the 52 Weeks Saving Challenge project
        users = UserProfile.objects.filter(
            projects__name='52 Weeks Saving Challenge',
            is_verified=True
        ).distinct()
        
        self.stdout.write(f"Found {users.count()} users to process")
        
        processed_count = 0
        total_interest = Decimal('0.00')
        
        for user_profile in users:
            # Check if already processed (look for existing transaction)
            existing = SavingsTransaction.objects.filter(
                user_profile=user_profile,
                receipt_number__startswith='UNINV-INT-2025'
            ).exists()
            
            if existing:
                self.stdout.write(
                    f"  ⊘ Skipped: {user_profile.user.get_username()} - Already processed"
                )
                continue
            
            # Calculate uninvested savings
            total_savings = SavingsTransaction.get_user_total_savings(user_profile)
            total_invested = sum(
                inv.amount_invested for inv in user_profile.investments.filter(status='fixed')
            )
            uninvested_amount = total_savings - total_invested
            
            if uninvested_amount <= 0:
                self.stdout.write(
                    f"  ⊘ Skipped: {user_profile.user.get_username()} - No uninvested savings"
                )
                continue
            
            # Calculate 15% interest
            interest_amount = uninvested_amount * Decimal('0.15')
            
            if dry_run:
                self.stdout.write(
                    f"  [DRY RUN] Would process: {user_profile.user.get_username()} - "
                    f"Uninvested: UGX {uninvested_amount:,.0f} - Interest (15%): UGX {interest_amount:,.0f}"
                )
            else:
                try:
                    with db_transaction.atomic():
                        interest_transaction = SavingsTransaction.objects.create(
                            user_profile=user_profile,
                            amount=interest_amount,
                            transaction_type='deposit',
                            transaction_date=date(2025, 12, 31),
                            receipt_number=f'UNINV-INT-2025-{user_profile.id}',
                        )
                        processed_count += 1
                        total_interest += interest_amount
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  ✓ Processed: {user_profile.user.get_username()} - "
                                f"Interest: UGX {interest_amount:,.0f}"
                            )
                        )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"  ✗ Error processing {user_profile.user.get_username()}: {str(e)}"
                        )
                    )
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nProcessed {processed_count} users. Total uninvested interest paid: UGX {total_interest:,.0f}"
                )
            )

    def transfer_challenge_savings(self, dry_run=False):
        """Transfer all 52WSC 2025 savings to user accounts on Jan 1, 2026"""
        self.stdout.write("\n=== Transferring 52WSC 2025 Savings to Accounts (Jan 1, 2026) ===")
        
        # Get all users with the 52 Weeks Saving Challenge project
        users = UserProfile.objects.filter(
            projects__name='52 Weeks Saving Challenge',
            is_verified=True
        ).distinct()
        
        self.stdout.write(f"Found {users.count()} users to process")
        
        processed_count = 0
        total_transferred = Decimal('0.00')
        
        for user_profile in users:
            # Check if already transferred (look for existing transaction)
            existing = SavingsTransaction.objects.filter(
                user_profile=user_profile,
                receipt_number__startswith='TRANSFER-2025-'
            ).exists()
            
            if existing:
                self.stdout.write(
                    f"  ⊘ Skipped: {user_profile.user.get_username()} - Already transferred"
                )
                continue
            
            # Calculate total savings (including all deposits and interest)
            total_savings = SavingsTransaction.get_user_total_savings(user_profile)
            
            if total_savings <= 0:
                self.stdout.write(
                    f"  ⊘ Skipped: {user_profile.user.get_username()} - No savings to transfer"
                )
                continue
            
            if dry_run:
                self.stdout.write(
                    f"  [DRY RUN] Would transfer: {user_profile.user.get_username()} - "
                    f"Amount: UGX {total_savings:,.0f}"
                )
            else:
                try:
                    with db_transaction.atomic():
                        # Create transfer transaction
                        transfer_transaction = SavingsTransaction.objects.create(
                            user_profile=user_profile,
                            amount=total_savings,
                            transaction_type='deposit',
                            transaction_date=date(2026, 1, 1),
                            receipt_number=f'TRANSFER-2025-{user_profile.id}-{date.today().strftime("%Y%m%d")}',
                        )
                        
                        # Note: In a real system, you would also:
                        # 1. Create a record in an account balance model
                        # 2. Archive or mark 2025 transactions
                        # 3. Reset for 2026 challenge
                        # For now, we just create the transfer transaction
                        
                        processed_count += 1
                        total_transferred += total_savings
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  ✓ Transferred: {user_profile.user.get_username()} - "
                                f"Amount: UGX {total_savings:,.0f}"
                            )
                        )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"  ✗ Error transferring {user_profile.user.get_username()}: {str(e)}"
                        )
                    )
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nTransferred savings for {processed_count} users. Total transferred: UGX {total_transferred:,.0f}"
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    "\nNOTE: This creates transfer transactions. You may want to implement "
                    "additional logic to archive 2025 data and prepare for 2026 challenge."
                )
            )

