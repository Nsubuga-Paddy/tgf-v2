from __future__ import annotations
from decimal import Decimal
from datetime import date
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Sum, Count
from django.utils import timezone
from accounts.models import UserProfile

# Constants
GOAT_UNIT_PRICE_DEFAULT = Decimal("600000.00")
CGF_CASHOUT_PRICE_PER_GOAT = Decimal("400000.00")  # Value per goat when selling/cashing out
ACCOUNT_GOAT_CAPACITY = 10

def get_receipt_prefix() -> str:
    """Generate the auto receipt prefix (RCPT-YYYYMMDD)"""
    return f"RCPT-{timezone.now().strftime('%Y%m%d')}"

def get_receipt_format_example() -> str:
    """Generate example receipt format for admin reference"""
    return f"{get_receipt_prefix()}-DCF001"

class Farm(models.Model):
    """Goat farms where users can invest"""
    name = models.CharField(max_length=100, unique=True)
    location = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    total_capacity = models.PositiveIntegerField(default=1000)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.location})"

    @property
    def current_goats(self) -> int:
        """Total goats currently in this farm"""
        return self.user_accounts.aggregate(
            total=Sum('current_goats')
        )['total'] or 0

    @property
    def available_capacity(self) -> int:
        """Remaining capacity in this farm"""
        return self.total_capacity - self.current_goats

    @property
    def capacity_percentage(self) -> float:
        """Percentage of farm capacity occupied"""
        if self.total_capacity == 0:
            return 0
        return (self.current_goats / self.total_capacity) * 100

class ManagementFeeTier(models.Model):
    """Management fee structure based on goat count"""
    min_goats = models.PositiveIntegerField()
    max_goats = models.PositiveIntegerField()
    annual_fee = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ['min_goats']
        unique_together = ('min_goats', 'max_goats')

    def __str__(self):
        return f"{self.min_goats}-{self.max_goats} goats: UGX {self.annual_fee:,.0f}"

    @classmethod
    def get_fee_for_goats(cls, goat_count: int) -> Decimal:
        """Get management fee for given number of goats"""
        tier = cls.objects.filter(
            min_goats__lte=goat_count,
            max_goats__gte=goat_count
        ).first()
        return tier.annual_fee if tier else Decimal('0.00')

class InvestmentPackage(models.Model):
    """Investment packages that users can purchase"""
    name = models.CharField(max_length=100)
    goat_count = models.PositiveIntegerField()
    goat_unit_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=GOAT_UNIT_PRICE_DEFAULT
    )
    kids_per_goat = models.PositiveSmallIntegerField(
        default=2,
        help_text="Expected kids per goat at end of 14-month cycle"
    )
    management_fee_tier = models.ForeignKey(
        ManagementFeeTier, 
        on_delete=models.PROTECT,
        help_text="Management fee tier for this package"
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.goat_count} goats"

    @property
    def goat_cost(self) -> Decimal:
        """Total cost for goats only"""
        return self.goat_count * self.goat_unit_price

    @property
    def management_fee(self) -> Decimal:
        """Management fee for this package"""
        return self.management_fee_tier.annual_fee

    @property
    def total_cost(self) -> Decimal:
        """Total package cost (goats + management fee)"""
        return self.goat_cost + self.management_fee

    @property
    def expected_kids_per_package(self) -> int:
        """Expected kids at end of 14-month cycle (goat_count * kids_per_goat)"""
        return self.goat_count * self.kids_per_goat

class UserFarmAccount(models.Model):
    """User's goat holdings in a specific farm"""
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='farm_accounts')
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='user_accounts')
    current_goats = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    expected_kids = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Admin override for expected kids at end of cycle. Leave blank to use calculated value from package."
    )
    created_at = models.DateTimeField(default=timezone.now, help_text="Account creation date (editable for backdating existing data)")

    class Meta:
        unique_together = ('user', 'farm')
        ordering = ['farm', 'user']

    def __str__(self):
        return f"{self.user.display_name} - {self.farm.name} ({self.current_goats} goats)"

class PackagePurchase(models.Model):
    """Record of a user purchasing an investment package"""
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='package_purchases')
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='package_purchases')
    package = models.ForeignKey(InvestmentPackage, on_delete=models.PROTECT)
    
    # Financial details
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Goat allocation
    goats_allocated = models.PositiveIntegerField(default=0)
    
    # Status
    STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('partial', 'Partially Paid'),
        ('paid', 'Fully Paid'),
        ('allocated', 'Goats Allocated'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    purchase_date = models.DateTimeField(default=timezone.now, help_text="Purchase date (editable for backdating existing data)")
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-purchase_date']

    def __str__(self):
        return f"{self.user.display_name} - {self.package.name} in {self.farm.name}"

    @property
    def balance_due(self) -> Decimal:
        """Remaining amount to be paid"""
        return self.total_amount - self.amount_paid

    @property
    def is_fully_paid(self) -> bool:
        """Check if package is fully paid"""
        return self.amount_paid >= self.total_amount

    @property
    def payment_percentage(self) -> float:
        """Percentage of payment completed"""
        if self.total_amount == 0:
            return 0
        return (self.amount_paid / self.total_amount) * 100

    def allocate_goats_to_accounts(self):
        """Automatically allocate goats to user's account in the farm"""
        if not self.is_fully_paid:
            return False

        goats_to_allocate = self.package.goat_count
        
        # Get or create user's account in this farm (one account per user per farm)
        user_account, created = UserFarmAccount.objects.get_or_create(
            user=self.user, 
            farm=self.farm,
            defaults={'is_active': True}
        )
        
        # Add goats to the account
        user_account.current_goats += goats_to_allocate
        user_account.save()

        # Update purchase record
        self.goats_allocated = goats_to_allocate
        self.status = 'allocated'
        self.save()
        
        return True

class Payment(models.Model):
    """Payment records for package purchases"""
    purchase = models.ForeignKey(PackagePurchase, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    receipt_prefix = models.CharField(
        max_length=20,
        default=get_receipt_prefix,
        help_text="Auto-generated prefix (RCPT-YYYYMMDD)"
    )
    receipt_suffix = models.CharField(
        max_length=20,
        help_text="Enter the suffix from your receipt book (e.g., DCF001, DCF002)"
    )
    receipt_number = models.CharField(
        max_length=50, 
        unique=True, 
        blank=True,
        help_text="Full receipt number (auto-generated from prefix + suffix)"
    )
    payment_method = models.CharField(max_length=50, blank=True)
    payment_date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-payment_date']

    def __str__(self):
        return f"Payment {self.receipt_number} - UGX {self.amount:,.0f}"

    def save(self, *args, **kwargs):
        # Auto-generate full receipt number from prefix + suffix
        if self.receipt_suffix:
            self.receipt_number = f"{self.receipt_prefix}-{self.receipt_suffix}"
        
        super().save(*args, **kwargs)
        
        # Update purchase amount_paid
        total_payments = self.purchase.payments.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        self.purchase.amount_paid = total_payments
        
        # Update purchase status
        if self.purchase.is_fully_paid:
            if self.purchase.goats_allocated == 0:
                self.purchase.status = 'paid'
            else:
                self.purchase.status = 'allocated'
        elif self.purchase.amount_paid > 0:
            self.purchase.status = 'partial'
        else:
            self.purchase.status = 'pending'
            
        self.purchase.save()


class CGFActionRequest(models.Model):
    """User action requests for Commercial Goat Farming (Sell & Cash Out, Take Goats, Transfer)"""
    REQUEST_TYPE_CHOICES = [
        ('sell_cash_out', 'Sell & Cash Out'),
        ('take_goats', 'Take Goats'),
        ('transfer', 'Transfer (Breeding → Commercial)'),
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
        related_name='cgf_action_requests'
    )
    request_type = models.CharField(
        max_length=30,
        choices=REQUEST_TYPE_CHOICES,
        help_text="Type of action requested"
    )
    goats_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of goats for this action (sell, take, or transfer)"
    )
    notes = models.TextField(blank=True, null=True, help_text="User notes or additional details")
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
        verbose_name = "CGF Action Request"
        verbose_name_plural = "CGF Action Requests"

    def __str__(self):
        return f"{self.user_profile.display_name} - {self.get_request_type_display()} ({self.get_status_display()})"

    @property
    def cash_value(self):
        """UGX value when selling goats (goats_count × price per goat). Used for sell_cash_out requests."""
        count = self.goats_count or 0
        return count * 400000  # UGX per goat


# Initialize default data
def setup_default_data():
    """Create default management fee tiers and packages"""
    # Management fee tiers
    ManagementFeeTier.objects.get_or_create(
        min_goats=1, max_goats=19,
        defaults={'annual_fee': Decimal('1000000.00')}
    )
    ManagementFeeTier.objects.get_or_create(
        min_goats=20, max_goats=39,
        defaults={'annual_fee': Decimal('2000000.00')}
    )
    
    # Get fee tiers
    tier_1_19 = ManagementFeeTier.objects.get(min_goats=1, max_goats=19)
    tier_20_39 = ManagementFeeTier.objects.get(min_goats=20, max_goats=39)
    
    # Investment packages
    InvestmentPackage.objects.get_or_create(
        name="Package 1 - 2 Goats",
        defaults={
            'goat_count': 2,
            'management_fee_tier': tier_1_19,
        }
    )
    InvestmentPackage.objects.get_or_create(
        name="Package 2 - 4 Goats", 
        defaults={
            'goat_count': 4,
            'management_fee_tier': tier_1_19,
        }
    )