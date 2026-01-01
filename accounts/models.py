# accounts/models.py
from __future__ import annotations

from decimal import Decimal
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

    # WhatsApp number (UG context), optional but unique if provided
    whatsapp_number = PhoneNumberField(
        region="UG",
        unique=True,
        null=True,
        blank=True,
        help_text="Include country code, e.g., +2567xxxxxxxx",
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

    # Bank account information (for withdrawals)
    bank_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Name of your bank"
    )
    bank_account_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Your bank account number"
    )
    bank_account_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Name on the bank account"
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
            # Unique only when not NULL
            models.UniqueConstraint(
                fields=["whatsapp_number"],
                name="uniq_whatsapp_when_set",
                condition=Q(whatsapp_number__isnull=False),
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
        Get total savings from all SavingsTransaction records.
        This method safely handles the case where the savings app might not be available.
        """
        try:
            # Use getattr to avoid circular import issues
            savings_transactions = getattr(self, 'savings_transactions', None)
            if savings_transactions:
                return savings_transactions.aggregate(
                    total=Coalesce(Sum("amount"), Value(Decimal("0.00"), output_field=DecimalField()))
                )["total"]
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
            for _ in range(5):
                candidate = self._generate_account_number(initials)
                self.account_number = candidate
                try:
                    with transaction.atomic():
                        return super().save(*args, **kwargs)
                except IntegrityError:
                    # Rare collision; retry with a fresh sequence
                    self.account_number = None
            # If we somehow still collide, bubble up the error
            raise
        return super().save(*args, **kwargs)

    # ---- Convenience helpers ----
    def add_project_by_name(self, name: str) -> Project:
        proj, _ = Project.objects.get_or_create(name=name)
        self.projects.add(proj)
        return proj
    def has_project(self, name: str) -> bool:
        return self.projects.filter(name=name).exists()


# -------------------------------------------------------------------
# Withdrawal Requests
# -------------------------------------------------------------------
class WithdrawalRequest(models.Model):
    """
    User withdrawal requests that require admin approval
    Money is withheld until admin approves after bank transfer
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved - Transfer Confirmed'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed - Amount Deducted'),
    ]
    
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='withdrawal_requests'
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text="Amount to withdraw"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Request status"
    )
    
    # Bank account details (snapshot at time of request)
    bank_name = models.CharField(max_length=100, help_text="Bank name")
    bank_account_number = models.CharField(max_length=50, help_text="Account number")
    bank_account_name = models.CharField(max_length=200, help_text="Account name")
    
    # Admin processing
    admin_notes = models.TextField(
        blank=True,
        help_text="Admin notes about this withdrawal"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_withdrawals',
        help_text="Admin who approved this withdrawal"
    )
    
    # Timestamps
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-requested_at']
        verbose_name = "Withdrawal Request"
        verbose_name_plural = "Withdrawal Requests"
    
    def __str__(self):
        return f"{self.user_profile.user.get_username()} - UGX {self.amount:,.0f} ({self.get_status_display()})"


# -------------------------------------------------------------------
# MESU Academy Share Interest
# -------------------------------------------------------------------
class MESUInterest(models.Model):
    """
    User interest in purchasing MESU Academy shares
    Money is held until admin approves, then deducted
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved - Processing'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed - Shares Purchased'),
    ]
    
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='mesu_interests'
    )
    shares_requested = models.PositiveIntegerField(
        help_text="Number of shares requested (1 share = 1M)"
    )
    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text="Total amount (shares × 1,000,000)"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Request status"
    )
    
    # Admin processing
    admin_notes = models.TextField(
        blank=True,
        help_text="Admin notes about this request"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_mesu_interests',
        help_text="Admin who approved this request"
    )
    
    # Timestamps
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-requested_at']
        verbose_name = "MESU Interest"
        verbose_name_plural = "MESU Interests"
    
    def __str__(self):
        return f"{self.user_profile.user.get_username()} - {self.shares_requested} shares (UGX {self.total_amount:,.0f})"
    
    def save(self, *args, **kwargs):
        # Auto-calculate total amount if not set
        if not self.total_amount and self.shares_requested:
            self.total_amount = Decimal(self.shares_requested) * Decimal('1000000')
        super().save(*args, **kwargs)


# -------------------------------------------------------------------
# Signals: auto-create a profile for each new user
# -------------------------------------------------------------------
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_user_profile(sender, instance, created, **kwargs):
    if created:
        # Create a bare profile (account number will be set on save)
        profile = UserProfile(user=instance)
        profile.save()
