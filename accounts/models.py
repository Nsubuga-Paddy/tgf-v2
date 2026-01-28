# accounts/models.py
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from datetime import date

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models, transaction, IntegrityError
from django.db.models import Sum, Value, Q
from django.db.models.fields import DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone

from django.dispatch import receiver
from django.db.models.signals import post_save
from phonenumber_field.modelfields import PhoneNumberField


# -------------------------------------------------------------------
# Helper model to produce a race-free, incrementing sequence
# -------------------------------------------------------------------
class AccountNumberCounter(models.Model):
    """
    Each new row gives us a unique, ever-increasing integer (id).
    We don't store business data here; we just use AutoField to avoid
    race conditions during account number generation.
    """
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Seq {self.pk}"


# -------------------------------------------------------------------
# Project (users can belong to multiple projects/apps)
# -------------------------------------------------------------------
class Project(models.Model):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


# -------------------------------------------------------------------
# Utilities / constants
# -------------------------------------------------------------------
def profile_photo_upload_to(instance: "UserProfile", filename: str) -> str:
    # e.g., profiles/42/2025/08/12/filename.jpg
    today = timezone.now()
    return f"profiles/{instance.user_id}/{today:%Y/%m/%d}/{filename}"


ACCOUNT_NUMBER_PREFIX = "MCSTGF"
# Example: MCSTGF-AB0001 (prefix-2 initials-4+ digits)
ACCOUNT_NUMBER_REGEX = r"^MCSTGF-[A-Z]{2}\d{4,}$"

NIN_VALIDATOR = RegexValidator(
    regex=r"^[A-Za-z0-9\-]{5,32}$",  # make looser/tighter as your NIN format requires
    message="National ID must be 5–32 characters (letters, numbers, or hyphen).",
)


# -------------------------------------------------------------------
# User Profile
# -------------------------------------------------------------------
class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    is_verified = models.BooleanField(default=False)

    # ---- Identity & contact ----
    photo = models.ImageField(upload_to=profile_photo_upload_to, blank=True, null=True)

    # WhatsApp number (UG context), required for contact purposes
    whatsapp_number = PhoneNumberField(
        region="UG",
        unique=True,
        null=False,
        blank=False,
        help_text="Include country code, e.g., +2567xxxxxxxx (Required for contact)",
    )

    # National ID (NIN) – optional; unique if provided
    national_id = models.CharField(
        max_length=32,
        unique=True,
        null=True,
        blank=True,
        validators=[NIN_VALIDATOR],
    )

    # Birthdate (optional)
    birthdate = models.DateField(null=True, blank=True)

    # Extra profile info (optional)
    address = models.TextField(blank=True, null=True)
    bio = models.TextField(blank=True, null=True)

    # Bank account information (for withdrawals/payments)
    bank_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Name of the bank (e.g., Centenary Bank, Stanbic Bank)",
    )
    bank_account_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Bank account number",
    )
    bank_account_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Name as it appears on the bank account",
    )

    # Access control & flags
    is_verified = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)

    # Account number like MCSTGF-AB0001 (auto-generated)
    account_number = models.CharField(
        max_length=32,
        unique=True,
        blank=True,
        null=True,
        db_index=True,
        help_text="Format: MCSTGF-AB0001 (auto-generated).",
    )

    # Multi-project access
    projects = models.ManyToManyField(
        Project,
        blank=True,
        related_name="members",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ---- Meta: indexes & constraints ----
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

        indexes = [
            models.Index(fields=["user"], name="idx_profile_user"),
            models.Index(fields=["account_number"], name="idx_profile_acct"),
            models.Index(fields=["whatsapp_number"], name="idx_profile_whatsapp"),
            models.Index(fields=["national_id"], name="idx_profile_nin"),
        ]

        # Conditional unique constraints let multiple NULLs coexist,
        # while still enforcing uniqueness when values are present.
        constraints = [
            # Enforce account number format when not NULL
            models.CheckConstraint(
                name="account_number_format_ok",
                check=Q(account_number__regex=ACCOUNT_NUMBER_REGEX) | Q(account_number__isnull=True),
            ),
            # WhatsApp number is now required, so always enforce uniqueness
            models.UniqueConstraint(
                fields=["whatsapp_number"],
                name="uniq_whatsapp",
            ),
            models.UniqueConstraint(
                fields=["national_id"],
                name="uniq_national_id_when_set",
                condition=Q(national_id__isnull=False),
            ),
        ]

    # ---- Dunders ----
    def __str__(self) -> str:
        return self.user.get_username()

    def get_absolute_url(self) -> str:
        # Return a default URL since profile_detail view doesn't exist yet
        return "/"

    # ---- Helpers / Derived fields ----
    @property
    def display_name(self) -> str:
        # Prefer first + last; fallback to username
        first = (self.user.first_name or "").strip()
        last = (self.user.last_name or "").strip()
        return f"{first} {last}".strip() or self.user.get_username()

    @property
    def initials(self) -> str:
        return self._initials_from_user(self.user)

    @property
    def age(self) -> int | None:
        if not self.birthdate:
            return None
        today = date.today()
        years = today.year - self.birthdate.year - (
            (today.month, today.day) < (self.birthdate.month, self.birthdate.day)
        )
        return max(0, years)

    def get_total_savings(self) -> Decimal:
        """
        Get total savings from all SavingsTransaction records including matured interest.
        This includes:
        - All deposits minus withdrawals
        - All interest gained from investments (matured or ongoing)
        - 15% interest on uninvested savings (if after Dec 31, 2025)
        """
        try:
            # Use getattr to avoid circular import issues
            savings_transactions = getattr(self, 'savings_transactions', None)
            if savings_transactions:
                # Get total deposits minus withdrawals and GWC contributions
                from django.db.models import Case, When, F, Value
                total = savings_transactions.aggregate(
                    total=Coalesce(
                        Sum(
                            Case(
                                When(transaction_type='deposit', then=F('amount')),
                                When(transaction_type='withdrawal', then=-F('amount')),
                                When(transaction_type='gwc_contribution', then=-F('amount')),
                                default=Value(Decimal("0.00")),
                                output_field=DecimalField()
                            )
                        ),
                        Value(Decimal("0.00"), output_field=DecimalField())
                    )
                )["total"] or Decimal("0.00")
                
                # Add all interest gained from investments (both matured and ongoing)
                investments = getattr(self, 'investments', None)
                if investments:
                    for investment in investments.filter(status__in=['fixed', 'matured']):
                        if hasattr(investment, 'interest_gained_so_far'):
                            total += investment.interest_gained_so_far
                
                # Add uninvested savings interest (15% on Dec 31, 2025)
                from datetime import date
                if date.today() >= date(2025, 12, 31):
                    # Calculate uninvested amount (before adding interest)
                    total_invested = self.get_total_investments()
                    # Get base savings (before interest)
                    base_savings = savings_transactions.aggregate(
                        total=Coalesce(
                            Sum(
                                Case(
                                    When(transaction_type='deposit', then=F('amount')),
                                    When(transaction_type='withdrawal', then=-F('amount')),
                                    When(transaction_type='gwc_contribution', then=-F('amount')),
                                    default=Value(Decimal("0.00")),
                                    output_field=DecimalField()
                                )
                            ),
                            Value(Decimal("0.00"), output_field=DecimalField())
                        )
                    )["total"] or Decimal("0.00")
                    uninvested = base_savings - total_invested if base_savings > total_invested else Decimal("0.00")
                    if uninvested > 0:
                        total += uninvested * Decimal("0.15")
                
                return total
        except Exception:
            pass
        return Decimal("0.00")

    def get_total_investments(self) -> Decimal:
        """
        Get total invested amount from all Investment records.
        This method safely handles the case where the savings app might not be available.
        """
        try:
            # Use getattr to avoid circular import issues
            investments = getattr(self, 'investments', None)
            if investments:
                return investments.aggregate(
                    total=Coalesce(Sum("amount_invested"), Value(Decimal("0.00"), output_field=DecimalField()))
                )["total"]
        except Exception:
            pass
        return Decimal("0.00")

    def get_total_interest_expected(self) -> Decimal:
        """
        Get total expected interest from all investments.
        This method safely handles the case where the savings app might not be available.
        """
        try:
            # Use getattr to avoid circular import issues
            investments = getattr(self, 'investments', None)
            if investments:
                total = Decimal("0.00")
                for investment in investments.all():
                    total += investment.interest_expected
                return total
        except Exception:
            pass
        return Decimal("0.00")

    def get_total_interest_gained(self) -> Decimal:
        """
        Get total interest gained so far from all investments.
        This method safely handles the case where the savings app might not be available.
        """
        try:
            # Use getattr to avoid circular import issues
            investments = getattr(self, 'investments', None)
            if investments:
                total = Decimal("0.00")
                for investment in investments.all():
                    total += investment.interest_gained_so_far
                return total
        except Exception:
            pass
        return Decimal("0.00")

    def get_amount_saved(self) -> Decimal:
        """
        Get the actual amount saved (deposits minus withdrawals) without any interest.
        This is the base savings amount before interest calculations.
        NOTE: For profile page, use get_current_year_amount_saved() instead.
        """
        try:
            savings_transactions = getattr(self, 'savings_transactions', None)
            if savings_transactions:
                from django.db.models import Case, When, F, Value
                total = savings_transactions.aggregate(
                    total=Coalesce(
                        Sum(
                            Case(
                                When(transaction_type='deposit', then=F('amount')),
                                When(transaction_type='withdrawal', then=-F('amount')),
                                When(transaction_type='gwc_contribution', then=-F('amount')),
                                default=Value(Decimal("0.00")),
                                output_field=DecimalField()
                            )
                        ),
                        Value(Decimal("0.00"), output_field=DecimalField())
                    )
                )["total"] or Decimal("0.00")
                return total
        except Exception:
            pass
        return Decimal("0.00")
    
    def get_current_year_amount_saved(self) -> Decimal:
        """
        Get current year deposits only (resets every year).
        This shows only deposits from the current year, no withdrawals/GWC deductions.
        """
        try:
            from django.utils import timezone
            current_year = timezone.now().year
            
            savings_transactions = getattr(self, 'savings_transactions', None)
            if savings_transactions:
                current_year_deposits = savings_transactions.filter(
                    transaction_type='deposit',
                    transaction_date__year=current_year
                ).aggregate(
                    total=Coalesce(Sum('amount'), Value(Decimal("0.00"), output_field=DecimalField()))
                )["total"] or Decimal("0.00")
                return current_year_deposits
        except Exception:
            pass
        return Decimal("0.00")

    def get_total_interest_earned(self) -> Decimal:
        """
        Get total interest earned including:
        - Interest from investments (matured and ongoing)
        - 15% interest on uninvested savings (if after Dec 31, 2025)
        NOTE: For profile page, use get_current_year_daily_interest() for current year interest.
        """
        total_interest = Decimal("0.00")
        
        # Add interest from investments
        try:
            investments = getattr(self, 'investments', None)
            if investments:
                for investment in investments.filter(status__in=['fixed', 'matured']):
                    if hasattr(investment, 'interest_gained_so_far'):
                        total_interest += investment.interest_gained_so_far
        except Exception:
            pass
        
        # Add uninvested savings interest (15% on Dec 31, 2025)
        try:
            if date.today() >= date(2025, 12, 31):
                savings_transactions = getattr(self, 'savings_transactions', None)
                if savings_transactions:
                    from django.db.models import Case, When, F
                    total_invested = self.get_total_investments()
                    base_savings = savings_transactions.aggregate(
                        total=Coalesce(
                            Sum(
                                Case(
                                    When(transaction_type='deposit', then=F('amount')),
                                    When(transaction_type='withdrawal', then=-F('amount')),
                                    When(transaction_type='gwc_contribution', then=-F('amount')),
                                    default=Value(Decimal("0.00")),
                                    output_field=DecimalField()
                                )
                            ),
                            Value(Decimal("0.00"), output_field=DecimalField())
                        )
                    )["total"] or Decimal("0.00")
                    uninvested = base_savings - total_invested if base_savings > total_invested else Decimal("0.00")
                    if uninvested > 0:
                        total_interest += uninvested * Decimal("0.15")
        except Exception:
            pass
        
        return total_interest
    
    def get_current_year_daily_interest(self) -> Decimal:
        """
        Get daily interest being earned on current year deposits (15% annualized).
        This calculates accumulated daily interest: (deposits * 0.15 / 365) * days_elapsed_in_year
        Same calculation as "Unfixed Savings Interest" card in member dashboard.
        """
        try:
            from django.utils import timezone
            from datetime import date
            
            current_year = timezone.now().year
            today = date.today()
            start_of_year = date(current_year, 1, 1)
            days_elapsed = (today - start_of_year).days + 1  # +1 to include today
            
            # Get current year deposits only (uninvested amount)
            current_year_deposits = self.get_current_year_amount_saved()
            
            # Subtract current year investments to get uninvested amount
            current_year_invested = Decimal("0.00")
            try:
                investments = getattr(self, 'investments', None)
                if investments:
                    for inv in investments.filter(start_date__year=current_year, status='fixed'):
                        current_year_invested += inv.amount_invested
            except Exception:
                pass
            
            uninvested_amount = current_year_deposits - current_year_invested if current_year_deposits > current_year_invested else Decimal("0.00")
            
            if uninvested_amount > 0:
                # Calculate daily interest rate (15% annual = 15/365 per day)
                daily_rate = Decimal("0.15") / Decimal("365")
                # Calculate accumulated interest for days elapsed so far
                daily_interest = uninvested_amount * daily_rate * Decimal(days_elapsed)
                return daily_interest.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except Exception:
            pass
        return Decimal("0.00")
    
    def get_current_year_total_savings_and_interest(self) -> Decimal:
        """
        Get total of current year deposits + daily interest gained.
        This is for the "Total Savings and Interest" display in profile page.
        """
        current_year_deposits = self.get_current_year_amount_saved()
        daily_interest = self.get_current_year_daily_interest()
        return current_year_deposits + daily_interest
    
    def get_previous_year_total_with_interest(self) -> Decimal:
        """
        Get total savings and interest from previous year that has matured.
        This is what's available for withdrawal (includes interest from last year).
        Includes:
        - Previous year deposits
        - Minus withdrawals and GWC contributions (regardless of year)
        - Plus interest from previous year investments
        - Plus 15% interest on uninvested savings from previous year (if past Dec 31)
        """
        try:
            from datetime import date
            from django.utils import timezone
            
            current_year = timezone.now().year
            previous_year = current_year - 1
            
            savings_transactions = getattr(self, 'savings_transactions', None)
            if not savings_transactions:
                return Decimal("0.00")
            
            # Get deposits from previous year only
            previous_year_deposits = savings_transactions.filter(
                transaction_type='deposit',
                transaction_date__year=previous_year
            ).aggregate(
                total=Coalesce(Sum('amount'), Value(Decimal("0.00"), output_field=DecimalField()))
            )["total"] or Decimal("0.00")
            
            # Subtract all withdrawals and GWC contributions (regardless of year)
            # These reduce the available balance from previous year savings
            all_withdrawals = savings_transactions.filter(
                transaction_type='withdrawal'
            ).aggregate(
                total=Coalesce(Sum('amount'), Value(Decimal("0.00"), output_field=DecimalField()))
            )["total"] or Decimal("0.00")
            
            all_gwc = savings_transactions.filter(
                transaction_type='gwc_contribution'
            ).aggregate(
                total=Coalesce(Sum('amount'), Value(Decimal("0.00"), output_field=DecimalField()))
            )["total"] or Decimal("0.00")
            
            # Base amount from previous year (after withdrawals/GWC)
            base_amount = previous_year_deposits - all_withdrawals - all_gwc
            if base_amount < 0:
                base_amount = Decimal("0.00")
            
            # Add interest from previous year investments
            previous_year_interest = Decimal("0.00")
            try:
                investments = getattr(self, 'investments', None)
                if investments:
                    # Get investments that started in previous year
                    for investment in investments.filter(start_date__year=previous_year):
                        if hasattr(investment, 'interest_gained_so_far'):
                            previous_year_interest += investment.interest_gained_so_far
            except Exception:
                pass
            
            # Add 15% interest on uninvested savings from previous year
            # This is calculated if we're past Dec 31 of previous year
            if date.today() >= date(previous_year, 12, 31):
                try:
                    # Calculate total invested from previous year
                    total_invested_prev_year = Decimal("0.00")
                    investments = getattr(self, 'investments', None)
                    if investments:
                        for inv in investments.filter(start_date__year=previous_year):
                            total_invested_prev_year += inv.amount_invested
                    
                    # Uninvested amount = previous year deposits (before withdrawals) - investments
                    # But we need to use deposits before withdrawals for the 15% calculation
                    uninvested_prev_year = previous_year_deposits - total_invested_prev_year
                    if uninvested_prev_year > 0:
                        previous_year_interest += uninvested_prev_year * Decimal("0.15")
                except Exception:
                    pass
            
            return base_amount + previous_year_interest
        except Exception:
            return Decimal("0.00")

    def get_pending_withdrawal_amount(self) -> Decimal:
        """Get total amount in pending withdrawal requests"""
        try:
            pending_withdrawals = self.withdrawal_requests.filter(status='pending')
            total = pending_withdrawals.aggregate(
                total=Coalesce(Sum('amount'), Value(Decimal("0.00"), output_field=DecimalField()))
            )["total"] or Decimal("0.00")
            return total
        except Exception:
            return Decimal("0.00")

    def get_pending_gwc_amount(self) -> Decimal:
        """Get total amount in pending GWC contributions"""
        try:
            pending_gwc = self.gwc_contributions.filter(status='pending')
            total = pending_gwc.aggregate(
                total=Coalesce(Sum('amount'), Value(Decimal("0.00"), output_field=DecimalField()))
            )["total"] or Decimal("0.00")
            return total
        except Exception:
            return Decimal("0.00")

    def get_pending_mesu_amount(self) -> Decimal:
        """Get total amount in pending MESU investments"""
        try:
            pending_mesu = self.mesu_interests.filter(status='pending')
            total = pending_mesu.aggregate(
                total=Coalesce(Sum('investment_amount'), Value(Decimal("0.00"), output_field=DecimalField()))
            )["total"] or Decimal("0.00")
            return total
        except Exception:
            return Decimal("0.00")

    def get_total_withheld_amount(self) -> Decimal:
        """Get total amount withheld in all pending requests"""
        return (
            self.get_pending_withdrawal_amount() +
            self.get_pending_gwc_amount() +
            self.get_pending_mesu_amount()
        )

    def get_available_balance(self) -> Decimal:
        """
        Get available balance for withdrawal.
        Includes total savings and interest from previous year that has matured.
        Withdrawals and GWC contributions are deducted from this amount.
        Current year savings are locked until the 52 weeks collapse (year end).
        """
        try:
            # Get previous year total with interest
            previous_year_total = self.get_previous_year_total_with_interest()
            
            # Subtract pending requests
            withheld = self.get_total_withheld_amount()
            available = previous_year_total - withheld
            
            return max(available, Decimal("0.00"))  # Don't go negative
        except Exception:
            return Decimal("0.00")

    # ---- Normalizers / Cleaners ----
    def clean(self):
        # Normalize National ID to uppercase & strip spaces/hyphens standardization if needed
        if self.national_id:
            self.national_id = self.national_id.strip().upper()

        # Optional: ensure address or bio length constraints in UI, not necessary here.

    # ---- Account number generation (race-safe) ----
    @staticmethod
    def _initials_from_user(user) -> str:
        """
        Get initials from last_name and first_name (in that order), uppercase.
        Fallback to 'XX' if both missing.
        """
        last_initial = (user.last_name or "").strip()[:1].upper() or "X"
        first_initial = (user.first_name or "").strip()[:1].upper() or "X"
        return f"{last_initial}{first_initial}"

    @classmethod
    def _generate_account_number(cls, initials: str) -> str:
        """
        Reserve a unique sequence using AccountNumberCounter to avoid races,
        then build MCSTGF-<INITIALS><SEQ> with zero-padded sequence.
        """
        with transaction.atomic():
            seq_row = AccountNumberCounter.objects.create()
            seq = seq_row.pk
            seq_str = str(seq).zfill(4)  # zero-pad to at least 4 digits
            return f"{ACCOUNT_NUMBER_PREFIX}-{initials}{seq_str}"

    def save(self, *args, **kwargs):
        """
        Auto-generate a collision-proof account_number on first save.
        Uses a counter table within a transaction to avoid race conditions.
        """
        creating = self.pk is None

        # Normalize before saving
        self.clean()

        if creating and not self.account_number:
            initials = self._initials_from_user(self.user)
            # Retry loop for extremely rare IntegrityError
            last_exception = None
            for attempt in range(5):
                candidate = self._generate_account_number(initials)
                self.account_number = candidate
                try:
                    with transaction.atomic():
                        return super().save(*args, **kwargs)
                except IntegrityError as e:
                    # Rare collision; retry with a fresh sequence
                    last_exception = e
                    self.account_number = None
            # If we somehow still collide after 5 attempts, raise the last exception
            if last_exception:
                raise last_exception
            # If no exception was caught but we still failed, raise a generic error
            raise IntegrityError(
                "Could not generate a unique account number after multiple attempts. "
                "Please try again or contact support."
            )
        return super().save(*args, **kwargs)

    # ---- Convenience helpers ----
    def add_project_by_name(self, name: str) -> Project:
        proj, _ = Project.objects.get_or_create(name=name)
        self.projects.add(proj)
        return proj
    def has_project(self, name: str) -> bool:
        return self.projects.filter(name=name).exists()


# -------------------------------------------------------------------
# Signals: auto-create a profile for each new user
# -------------------------------------------------------------------
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_user_profile(sender, instance, created, **kwargs):
    """
    Auto-create a UserProfile when a User is created.
    Note: whatsapp_number is required, so this signal will only create a profile
    if one doesn't already exist. The signup view should handle setting whatsapp_number
    immediately after user creation.
    """
    if created:
        # Only create profile if it doesn't exist
        if not hasattr(instance, 'profile') or not instance.profile:
            try:
                # The signup view will set whatsapp_number immediately after user creation
                # If profile creation fails here, the signup view will handle it
                profile = UserProfile(user=instance)
                profile.save()
            except Exception:
                # If profile creation fails (e.g., missing whatsapp_number),
                # the signup view will handle creating it with the phone number
                # This is expected behavior during signup
                pass


# -------------------------------------------------------------------
# Withdrawal Request Model
# -------------------------------------------------------------------
class WithdrawalRequest(models.Model):
    """Model to track user withdrawal requests"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('processed', 'Processed'),
    ]
    
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='withdrawal_requests'
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Withdrawal amount in UGX"
    )
    reason = models.TextField(blank=True, null=True, help_text="Reason for withdrawal")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    admin_notes = models.TextField(blank=True, null=True, help_text="Admin notes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Withdrawal Request"
        verbose_name_plural = "Withdrawal Requests"
    
    def __str__(self):
        return f"{self.user_profile.display_name} - UGX {self.amount:,.0f} - {self.get_status_display()}"
    
    def save(self, *args, **kwargs):
        """Override save to automatically create SavingsTransaction when approved"""
        # Get the old status if this is an update
        old_status = None
        if self.pk:
            try:
                old_instance = WithdrawalRequest.objects.get(pk=self.pk)
                old_status = old_instance.status
            except WithdrawalRequest.DoesNotExist:
                pass
        
        # Save the model first
        super().save(*args, **kwargs)
        
        # If status changed to 'approved' and we haven't created a transaction yet
        if self.status == 'approved' and old_status != 'approved':
            # Check if a transaction already exists for this withdrawal request
            try:
                from savings_52_weeks.models import SavingsTransaction
                existing_transaction = SavingsTransaction.objects.filter(
                    withdrawal_request=self
                ).first()
                
                if not existing_transaction:
                    # Create a withdrawal transaction
                    SavingsTransaction.objects.create(
                        user_profile=self.user_profile,
                        amount=self.amount,
                        transaction_type='withdrawal',
                        transaction_date=timezone.now().date(),
                        receipt_number=f"WDR-{self.pk}",
                        withdrawal_request=self,
                        # For withdrawals, we don't calculate covered weeks
                        fully_covered_weeks=[],
                        remaining_balance=Decimal("0.00"),
                        cumulative_total=Decimal("0.00"),
                        next_week=1,
                    )
            except Exception as e:
                # Log error but don't fail the save
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error creating withdrawal transaction: {e}")


# -------------------------------------------------------------------
# GWC Contribution Model
# -------------------------------------------------------------------
class GWCContribution(models.Model):
    """Model to track GWC group contributions"""
    GROUP_TYPE_CHOICES = [
        ('individual', 'Individual Contribution'),
        ('group', 'Group Contribution'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('processed', 'Processed'),
    ]
    
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='gwc_contributions'
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Contribution amount in UGX"
    )
    group_type = models.CharField(
        max_length=20,
        choices=GROUP_TYPE_CHOICES,
        help_text="Type of contribution"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    admin_notes = models.TextField(blank=True, null=True, help_text="Admin notes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "GWC Contribution"
        verbose_name_plural = "GWC Contributions"
    
    def __str__(self):
        return f"{self.user_profile.display_name} - UGX {self.amount:,.0f} ({self.get_group_type_display()}) - {self.get_status_display()}"
    
    def save(self, *args, **kwargs):
        """Override save to automatically create SavingsTransaction when approved"""
        # Get the old status if this is an update
        old_status = None
        if self.pk:
            try:
                old_instance = GWCContribution.objects.get(pk=self.pk)
                old_status = old_instance.status
            except GWCContribution.DoesNotExist:
                pass
        
        # Save the model first
        super().save(*args, **kwargs)
        
        # If status changed to 'approved' and we haven't created a transaction yet
        if self.status == 'approved' and old_status != 'approved':
            # Check if a transaction already exists for this GWC contribution
            try:
                from savings_52_weeks.models import SavingsTransaction
                existing_transaction = SavingsTransaction.objects.filter(
                    gwc_contribution=self
                ).first()
                
                if not existing_transaction:
                    # Create a GWC contribution transaction
                    SavingsTransaction.objects.create(
                        user_profile=self.user_profile,
                        amount=self.amount,
                        transaction_type='gwc_contribution',
                        transaction_date=timezone.now().date(),
                        receipt_number=f"GWC-{self.pk}",
                        gwc_contribution=self,
                        # For GWC contributions, we don't calculate covered weeks
                        fully_covered_weeks=[],
                        remaining_balance=Decimal("0.00"),
                        cumulative_total=Decimal("0.00"),
                        next_week=1,
                    )
            except Exception as e:
                # Log error but don't fail the save
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error creating GWC contribution transaction: {e}")


# -------------------------------------------------------------------
# MESU Interest Model
# -------------------------------------------------------------------
class MESUInterest(models.Model):
    """Model to track user interest in MESU Academy shares"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('processed', 'Processed'),
    ]
    
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='mesu_interests'
    )
    investment_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Investment amount in UGX"
    )
    number_of_shares = models.PositiveIntegerField(
        default=0,
        help_text="Number of shares (calculated: 1 share = UGX 1,000,000)"
    )
    notes = models.TextField(blank=True, null=True, help_text="Additional notes from user")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    admin_notes = models.TextField(blank=True, null=True, help_text="Admin notes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "MESU Interest"
        verbose_name_plural = "MESU Interests"
    
    def __str__(self):
        investment_amt = self.investment_amount or 0
        shares = self.number_of_shares or 0
        return f"{self.user_profile.display_name} - {shares} shares (UGX {investment_amt:,.0f}) - {self.get_status_display()}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate number of shares (1 share = 1,000,000 UGX)
        if self.investment_amount:
            self.number_of_shares = int(self.investment_amount / Decimal('1000000'))
        super().save(*args, **kwargs)
