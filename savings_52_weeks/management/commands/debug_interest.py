"""
Debug command to check why interest isn't being processed
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from savings_52_weeks.models import Investment, SavingsTransaction
from accounts.models import UserProfile


class Command(BaseCommand):
    help = 'Debug interest processing - shows why investments might not be processing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Username to check (optional)',
        )

    def handle(self, *args, **options):
        username = options.get('user')
        today = timezone.localdate()
        
        self.stdout.write(f"Today's date: {today}")
        self.stdout.write("=" * 60)
        
        if username:
            try:
                from django.contrib.auth.models import User
                user = User.objects.get(username=username)
                user_profiles = [user.profile] if hasattr(user, 'profile') else []
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"User '{username}' not found"))
                return
        else:
            # Get all users with 52WSC project
            user_profiles = UserProfile.objects.filter(
                projects__name='52 Weeks Saving Challenge',
                is_verified=True
            ).distinct()
        
        for user_profile in user_profiles:
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"User: {user_profile.user.get_username()}")
            self.stdout.write(f"Account: {user_profile.account_number}")
            self.stdout.write(f"{'='*60}")
            
            # Get all investments
            investments = Investment.objects.filter(user_profile=user_profile)
            
            if not investments.exists():
                self.stdout.write("  No investments found")
                continue
            
            self.stdout.write(f"\nTotal Investments: {investments.count()}")
            
            for inv in investments:
                self.stdout.write(f"\n  Investment #{inv.id}:")
                self.stdout.write(f"    Amount: UGX {inv.amount_invested:,.0f}")
                self.stdout.write(f"    Interest Rate: {inv.interest_rate}%")
                self.stdout.write(f"    Start Date: {inv.start_date}")
                self.stdout.write(f"    Maturity Date: {inv.maturity_date}")
                self.stdout.write(f"    Status: {inv.status}")
                self.stdout.write(f"    Interest Paid: {inv.interest_paid}")
                self.stdout.write(f"    Interest Paid Date: {inv.interest_paid_date or 'N/A'}")
                
                # Check maturity
                days_until = (inv.maturity_date - today).days
                if days_until < 0:
                    self.stdout.write(self.style.WARNING(f"    ⚠️  Matured {abs(days_until)} days ago"))
                elif days_until == 0:
                    self.stdout.write(self.style.WARNING("    ⚠️  Matures TODAY"))
                else:
                    self.stdout.write(f"    ⏳ Matures in {days_until} days")
                
                # Check if should be processed
                if inv.interest_paid:
                    self.stdout.write(self.style.SUCCESS("    ✅ Interest already paid"))
                elif inv.maturity_date <= today:
                    if inv.status != 'matured':
                        self.stdout.write(self.style.WARNING("    ⚠️  Should be processed (status needs update)"))
                    else:
                        self.stdout.write(self.style.ERROR("    ❌ Should be processed but hasn't been!"))
                    
                    # Calculate expected interest
                    expected_interest = inv.total_interest_expected
                    self.stdout.write(f"    Expected Interest: UGX {expected_interest:,.0f}")
                    
                    # Check if transaction exists
                    existing_tx = SavingsTransaction.objects.filter(
                        user_profile=user_profile,
                        receipt_number__startswith=f'INT-{inv.id}-'
                    ).first()
                    
                    if existing_tx:
                        self.stdout.write(self.style.SUCCESS(f"    ✅ Interest transaction exists: {existing_tx.receipt_number}"))
                    else:
                        self.stdout.write(self.style.ERROR("    ❌ No interest transaction found"))
                else:
                    self.stdout.write("    ⏳ Not matured yet")
            
            # Check total savings
            total_savings = SavingsTransaction.get_user_total_savings(user_profile)
            self.stdout.write(f"\n  Total Savings: UGX {total_savings:,.0f}")
            
            # Check for interest transactions
            interest_transactions = SavingsTransaction.objects.filter(
                user_profile=user_profile,
                receipt_number__startswith='INT-'
            )
            if interest_transactions.exists():
                self.stdout.write(f"\n  Interest Transactions Found: {interest_transactions.count()}")
                for tx in interest_transactions:
                    self.stdout.write(f"    - {tx.receipt_number}: UGX {tx.amount:,.0f} on {tx.transaction_date}")

