from django.db import models

# Create your models here.
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Sum, DecimalField, Value
from django.db.models.functions import Coalesce
from django.utils import timezone



# Import UserProfile from accounts app
from accounts.models import UserProfile


# ---------- helpers ----------

def add_months(d: date, months: int) -> date:
    """
    Add `months` to a date without using external deps.
    Handles year rollovers and end-of-month clamping (e.g., Jan 31 + 1 month -> Feb 28/29).
    """
    if not isinstance(d, (date, datetime)):
        raise TypeError("add_months expects a date/datetime")
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    # clamp day to last day of target month
    # days per month (simple; Feb leap handled by try/except)
    days_in_month = [31, 29 if (y % 400 == 0 or (y % 4 == 0 and y % 100 != 0)) else 28,
                     31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
    day = min(d.day, days_in_month)
    return date(y, m, day)


class SavingsTransaction(models.Model):
    """
    A savings deposit that automatically calculates which weeks are covered.
    The system distributes the saved amount across weeks 1-52 based on the 52-week challenge formula.
    """
    TRANSACTION_TYPE_CHOICES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('adjustment', 'Adjustment'),
        ('gwc_contribution', 'GWC Contribution'),
    ]

    user_profile = models.ForeignKey(
        UserProfile, on_delete=models.CASCADE, related_name="savings_transactions"
    )

    # Money as Decimal for precision
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Deposit amount in UGX"
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES,
        default='deposit',
        help_text="Type of transaction"
    )

    transaction_date = models.DateField(default=date.today)
    
    receipt_number = models.CharField(
        max_length=32,
        blank=True,
        null=True,
        help_text="Receipt or reference number for this deposit"
    )
    
    # Optional links to withdrawal/GWC requests (using string reference to avoid circular import)
    withdrawal_request = models.ForeignKey(
        'accounts.WithdrawalRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='savings_transactions',
        help_text="Linked withdrawal request (if this transaction is from a withdrawal)"
    )
    
    gwc_contribution = models.ForeignKey(
        'accounts.GWCContribution',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='savings_transactions',
        help_text="Linked GWC contribution (if this transaction is from a GWC contribution)"
    )

    date_saved = models.DateTimeField(default=timezone.now)

    # Denormalized / cached values for reporting (keep in sync)
    cumulative_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    fully_covered_weeks = models.JSONField(default=list, blank=True)
    next_week = models.PositiveIntegerField(default=1)
    remaining_balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date_saved"]
        indexes = [
            models.Index(fields=["user_profile", "date_saved"]),
            models.Index(fields=["date_saved"]),
        ]

    def __str__(self):
        d = self.date_saved.astimezone(timezone.get_current_timezone()).date() if self.date_saved else "—"
        return f"{self.user_profile.user.get_username()} - UGX {self.amount:,.2f} on {d}"

    # Example utility if you ever recompute denormalized fields:
    def quantize_money(self, value: Decimal) -> Decimal:
        return (value or Decimal("0.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    
    def calculate_covered_weeks(self):
        """
        Allocate this deposit + previous BF to the 52-week challenge WITHOUT partial weeks.
        If you cannot fully cover the next week, stop and carry the remainder as BF.

        Week N target = N * 10,000 UGX
        """
        if self.transaction_type not in ('deposit',):
            # Only deposits participate in week coverage logic
            # Withdrawals and GWC contributions don't affect week coverage
            self.fully_covered_weeks = []
            self.remaining_balance = Decimal("0.00")
            self.cumulative_total = Decimal("0.00")
            self.next_week = 1
            return

        profile = self.user_profile

        # Week targets (as Decimals)
        week_targets = {w: Decimal(w) * Decimal("10000") for w in range(1, 53)}

        # Bring forward any unallocated balance from the last deposit
        previous_balance = self._get_user_previous_balance(profile)

        # Where do we start allocating from?
        start_week = self._find_next_week_needing_funding(profile)

        # Total funds available to allocate this round
        total_available = (previous_balance or Decimal("0.00")) + (self.amount or Decimal("0.00"))
        remaining = total_available

        covered_weeks = []
        # We will only add entries for weeks fully covered on THIS transaction
        # (historical fully covered weeks are already recognized by _find_next_week_needing_funding)

        current_week = start_week
        while current_week <= 52 and remaining > 0:
            target = week_targets[current_week]

            # IMPORTANT: do NOT partially fund a week.
            # If we can't fully cover 'current_week', stop and carry the rest as BF.
            if remaining >= target:
                covered_weeks.append({
                    'week': current_week,
                    'week_target': str(target),
                    'amount_needed': str(target),              # we always allocate target (full week)
                    'amount_allocated': str(target),
                    'fully_covered': True,
                    # show previous BF for the very first week we cover in THIS tx; otherwise 0
                    'balance_brought_forward': str(previous_balance if current_week == start_week else Decimal("0.00")),
                    # cumulative_total here reflects this transaction's running allocation from total_available
                    'cumulative_total': str((total_available - (remaining - target)))
                })
                remaining -= target
                current_week += 1
            else:
                # Can't fully cover current_week; keep all as BF and stop
                break

        # Save results on the object
        self.fully_covered_weeks = covered_weeks
        self.remaining_balance = remaining
        self.cumulative_total = total_available

        # Compute next week to cover AFTER considering what we just fully covered
        if covered_weeks:
            next_week_to_cover = covered_weeks[-1]['week'] + 1
        else:
            next_week_to_cover = start_week

        # Cap at 53 = "all done"
        self.next_week = 53 if next_week_to_cover > 52 else next_week_to_cover



    def _get_week_savings(self, profile, week):
        """Get the current savings amount for a specific week"""
        # For now, return 0 as placeholder
        # In the future, this could track savings per week or use a different logic
        return Decimal("0.00")
    
    def _get_user_previous_balance(self, profile):
        """Get the user's previous balance brought forward from previous transactions in the same year"""
        try:
            # Get the transaction date year to filter by same year
            transaction_year = self.transaction_date.year if hasattr(self, 'transaction_date') and self.transaction_date else timezone.now().year
            
            # Get the most recent transaction from the same year to see what balance was brought forward
            latest_transaction = profile.savings_transactions.filter(
                transaction_type='deposit',
                transaction_date__year=transaction_year
            ).exclude(pk=self.pk).order_by('-created_at').first()
            
            if latest_transaction and latest_transaction.remaining_balance:
                return latest_transaction.remaining_balance
            else:
                return Decimal("0.00")
        except Exception:
            return Decimal("0.00")
    
    def _find_next_week_needing_funding(self, profile):
        """Find the next week that needs funding based on previous transactions in the same year"""
        try:
            # Get the transaction date year to filter by same year
            transaction_year = self.transaction_date.year if hasattr(self, 'transaction_date') and self.transaction_date else timezone.now().year
            
            # Get all previous transactions from the same year to see which weeks are already covered
            previous_transactions = profile.savings_transactions.filter(
                transaction_type='deposit',
                transaction_date__year=transaction_year
            ).exclude(pk=self.pk).order_by('created_at')
            
            covered_weeks = set()
            for transaction in previous_transactions:
                if transaction.fully_covered_weeks:
                    for week_data in transaction.fully_covered_weeks:
                        if week_data.get('fully_covered', False):
                            covered_weeks.add(week_data['week'])
            
            # Find the first week that's not fully covered
            for week in range(1, 53):
                if week not in covered_weeks:
                    return week
            
            # All weeks are covered
            return 53
            
        except Exception:
            return 1
    
    @classmethod
    def get_user_total_savings(cls, profile):
        """Get total savings for a user profile"""
        try:
            return profile.savings_transactions.filter(
                transaction_type='deposit'
            ).aggregate(
                total=models.Sum('amount')
            )['total'] or Decimal('0.00')
        except Exception:
            return Decimal('0.00')
    
    @classmethod
    def get_user_challenge_progress(cls, profile, year=None):
        """Get user's progress in the 52-week challenge for a specific year"""
        try:
            # Use current year if not specified
            if year is None:
                year = timezone.now().year
            
            # Get all deposit transactions from the specified year
            deposits = profile.savings_transactions.filter(
                transaction_type='deposit',
                transaction_date__year=year
            )
            
            total_saved = Decimal('0.00')
            covered_weeks = []
            
            for deposit in deposits:
                total_saved += deposit.amount
                if deposit.fully_covered_weeks:
                    covered_weeks.extend(deposit.fully_covered_weeks)
            
            # Calculate total target for 52 weeks
            total_target = Decimal('13780000')  # 13,780,000 UGX
            
            # Calculate progress percentage
            progress_percentage = (total_saved / total_target * 100) if total_target > 0 else 0
            
            return {
                'total_saved': total_saved,
                'total_target': total_target,
                'progress_percentage': min(progress_percentage, 100),
                'covered_weeks': covered_weeks,
                'weeks_completed': len(set(item['week'] for item in covered_weeks if item.get('fully_covered', False))),
                'total_weeks': 52,
                'year': year
            }
        except Exception:
            current_year = timezone.now().year if year is None else year
            return {
                'total_saved': Decimal('0.00'),
                'total_target': Decimal('13780000'),
                'progress_percentage': 0,
                'covered_weeks': [],
                'weeks_completed': 0,
                'total_weeks': 52,
                'year': current_year
            }
    
    def get_week_amount(self, week_data):
        """Helper method to get numeric amount from week data"""
        try:
            return Decimal(week_data.get('amount', '0'))
        except (ValueError, TypeError):
            return Decimal('0')
    
    def get_week_target(self, week_data):
        """Helper method to get numeric target from week data"""
        try:
            return Decimal(week_data.get('week_target', '0'))
        except (ValueError, TypeError):
            return Decimal('0')

    def save(self, *args, **kwargs):
        """Override save to automatically calculate covered weeks"""
        if self.transaction_type == 'deposit':
            self.calculate_covered_weeks()
        super().save(*args, **kwargs)


class Investment(models.Model):
    """
    Member investment with simple interest over a given number of months.
    """
    INVESTMENT_TYPE_CHOICES = [
        ('fixed_deposit', 'Fixed Deposit'),
        ('savings_bond', 'Savings Bond'),
        ('mutual_fund', 'Mutual Fund'),
        ('real_estate', 'Real Estate'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('fixed', 'Fixed'),
        ('matured', 'Matured'),
    ]

    user_profile = models.ForeignKey(
        UserProfile, on_delete=models.CASCADE, related_name="investments"
    )

    investment_type = models.CharField(
        max_length=20,
        choices=INVESTMENT_TYPE_CHOICES,
        default='fixed_deposit',
        help_text="Type of investment"
    )

    amount_invested = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Principal in UGX"
    )

    # Rate as Decimal to avoid float precision issues (0–100 range)
    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
        help_text="Annual simple interest rate, e.g. 30.00 for 30%"
    )

    maturity_months = models.PositiveIntegerField(default=8, help_text="Term length in months")
    start_date = models.DateField(default=date.today)
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='fixed',
        help_text="Current status of the investment"
    )
    
    notes = models.TextField(blank=True, help_text="Additional notes about this investment")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user_profile", "start_date"]),
            models.Index(fields=["start_date"]),
        ]

    def __str__(self):
        return f"{self.user_profile.user.get_username()} - UGX {self.amount_invested:,.2f} @ {self.interest_rate}% ({self.get_investment_type_display()})"

    @property
    def maturity_date(self) -> date:
        return add_months(self.start_date, self.maturity_months)

    @property
    def total_interest_expected(self) -> Decimal:
        """
        Simple interest over the full term: P * r * (months/12)
        """
        p = self.amount_invested or Decimal("0")
        r = (self.interest_rate or Decimal("0")) / Decimal("100")
        t = Decimal(self.maturity_months) / Decimal("12")
        return (p * r * t).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def interest_gained_so_far(self) -> Decimal:
        """
        Simple interest accrued by days elapsed so far (capped at term).
        This provides daily interest calculation for more accurate tracking.
        """
        today = timezone.localdate()
        if today < self.start_date:
            return Decimal("0.00")
        
        # Calculate days elapsed since start
        days_elapsed = (today - self.start_date).days
        
        # Cap at maturity date
        maturity_days = (self.maturity_date - self.start_date).days
        days_elapsed = min(days_elapsed, maturity_days)
        
        if days_elapsed <= 0:
            return Decimal("0.00")
        
        # Calculate daily interest rate and apply
        p = self.amount_invested or Decimal("0")
        r = (self.interest_rate or Decimal("0")) / Decimal("100")
        daily_rate = r / Decimal("365")  # Daily interest rate
        
        # Calculate interest for exact days elapsed
        daily_interest = p * daily_rate * Decimal(days_elapsed)
        return daily_interest.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def daily_interest_rate(self) -> Decimal:
        """Daily interest rate for this investment"""
        r = (self.interest_rate or Decimal("0")) / Decimal("100")
        return (r / Decimal("365")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    @property
    def interest_earned_today(self) -> Decimal:
        """Interest earned just today"""
        today = timezone.localdate()
        if today < self.start_date or today > self.maturity_date:
            return Decimal("0.00")
        
        p = self.amount_invested or Decimal("0")
        daily_rate = self.daily_interest_rate
        return (p * daily_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def days_since_start(self) -> int:
        """Days elapsed since investment start"""
        today = timezone.localdate()
        if today < self.start_date:
            return 0
        return (today - self.start_date).days

    @property
    def interest_progress_percentage(self) -> Decimal:
        """Percentage of total expected interest earned so far"""
        if self.total_interest_expected <= 0:
            return Decimal("0.00")
        
        earned = self.interest_gained_so_far
        return (earned / self.total_interest_expected * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def calculate_interest_for_period(self, start_date: date, end_date: date) -> Decimal:
        """
        Calculate interest earned for a specific date range.
        Useful for monthly/weekly interest reports.
        """
        if end_date < start_date:
            return Decimal("0.00")
        
        # Ensure dates are within investment period
        period_start = max(start_date, self.start_date)
        period_end = min(end_date, self.maturity_date)
        
        if period_start > period_end:
            return Decimal("0.00")
        
        # Calculate days in period
        days_in_period = (period_end - period_start).days + 1
        
        # Calculate interest for this period
        p = self.amount_invested or Decimal("0")
        daily_rate = self.daily_interest_rate
        period_interest = p * daily_rate * Decimal(days_in_period)
        
        return period_interest.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def check_and_update_status(self):
        """
        Automatically check if investment has matured and update status.
        Returns True if status was changed, False otherwise.
        Also creates a deposit transaction for matured interest.
        """
        if self.status == 'matured':
            return False  # Already matured
            
        today = timezone.localdate()
        if today >= self.maturity_date:
            old_status = self.status
            self.status = 'matured'
            self.save(update_fields=['status'])
            
            # If status changed to matured, create deposit transaction for interest
            if old_status != 'matured':
                try:
                    # Check if a transaction already exists for this matured investment
                    existing_transaction = SavingsTransaction.objects.filter(
                        receipt_number=f"INT-{self.pk}"
                    ).first()
                    
                    if not existing_transaction:
                        # Get the full interest amount (at maturity)
                        interest_amount = self.total_interest_expected
                        
                        if interest_amount > 0:
                            # Create a deposit transaction for the matured interest
                            SavingsTransaction.objects.create(
                                user_profile=self.user_profile,
                                amount=interest_amount,
                                transaction_type='deposit',
                                transaction_date=today,
                                receipt_number=f"INT-{self.pk}",
                                # For interest deposits, we don't calculate covered weeks
                                # They're just added to the balance
                                fully_covered_weeks=[],
                                remaining_balance=Decimal("0.00"),
                                cumulative_total=Decimal("0.00"),
                                next_week=1,
                            )
                except Exception as e:
                    # Log error but don't fail the save
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error creating matured interest transaction: {e}")
            
            return old_status != 'matured'
        return False

    @property
    def is_matured(self) -> bool:
        """Check if investment has matured based on current date"""
        return timezone.localdate() >= self.maturity_date

    @property
    def days_until_maturity(self) -> int:
        """Days remaining until maturity (negative if matured)"""
        today = timezone.localdate()
        delta = self.maturity_date - today
        return delta.days

    @classmethod
    def check_all_investments_status(cls):
        """
        Check and update status for all investments.
        Returns list of investments that matured.
        """
        matured_investments = []
        fixed_investments = cls.objects.filter(status='fixed')
        
        for investment in fixed_investments:
            if investment.check_and_update_status():
                matured_investments.append(investment)
        
        return matured_investments

    @classmethod
    def get_daily_interest_summary(cls, target_date: date = None):
        """
        Get daily interest summary for all active investments.
        Returns summary of interest earned today and total interest.
        """
        if target_date is None:
            target_date = timezone.localdate()
        
        active_investments = cls.objects.filter(status='fixed')
        
        daily_interest_total = Decimal("0.00")
        total_interest_earned = Decimal("0.00")
        investment_count = 0
        
        for investment in active_investments:
            if investment.start_date <= target_date <= investment.maturity_date:
                daily_interest_total += investment.interest_earned_today
                total_interest_earned += investment.interest_gained_so_far
                investment_count += 1
        
        return {
            'date': target_date,
            'daily_interest_total': daily_interest_total,
            'total_interest_earned': total_interest_earned,
            'active_investments': investment_count,
            'average_daily_interest': (daily_interest_total / investment_count) if investment_count > 0 else Decimal("0.00")
        }


# Note: UserProfile creation is handled by the accounts app signal
# No need to duplicate the signal here
