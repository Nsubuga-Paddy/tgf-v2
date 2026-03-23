"""
Generational Wealth Creation — fixed deposits and member-facing activity feed.
"""
from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class GWCDepositActivity(models.Model):
    """Timeline entries shown on the member dashboard (e.g. deposit funded, manual notes)."""

    class ActivityType(models.TextChoices):
        CREDIT = "credit", "Credit"
        DEBIT = "debit", "Debit"
        INFO = "info", "Info"

    deposit = models.ForeignKey(
        "GWCFixedDeposit",
        on_delete=models.CASCADE,
        related_name="activities",
    )
    description = models.CharField(max_length=255)
    activity_type = models.CharField(
        max_length=20,
        choices=ActivityType.choices,
        default=ActivityType.INFO,
    )
    amount = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="UGX amount when applicable.",
    )
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp", "-pk"]
        verbose_name = "GWC deposit activity"
        verbose_name_plural = "GWC deposit activities"

    def __str__(self) -> str:
        did = getattr(self.deposit, "deposit_id", None) or f"#{getattr(self.deposit, 'pk', '')}"
        return f"{did}: {self.description}"


class GWCFixedDeposit(models.Model):
    """A user's GWC fixed-term deposit (terms + lifecycle status)."""

    class Status(models.TextChoices):
        ACTIVE = "Active", "Active"
        MATURED = "Matured", "Matured"
        WITHDRAWN = "Withdrawn", "Withdrawn"
        CANCELLED = "Cancelled", "Cancelled"

    class InterestMethod(models.TextChoices):
        SIMPLE = "simple", "Simple"
        COMPOUND = "compound", "Compound"

    class CompoundingFrequency(models.TextChoices):
        DAILY = "daily", "Daily"
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        ANNUALLY = "annually", "Annually"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="gwc_fixed_deposits",
    )
    deposit_id = models.CharField(
        max_length=32,
        unique=True,
        editable=False,
        blank=True,
        db_index=True,
        help_text="Auto-generated public reference (e.g. GWC-2026-00042).",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )

    receipt_number = models.CharField(
        max_length=64,
        help_text="Physical / admin receipt reference for this deposit.",
    )
    principal_amount = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        help_text="Amount fixed (principal), UGX.",
    )
    transaction_date = models.DateField(
        help_text="Date the deposit transaction was recorded / received.",
    )
    start_date = models.DateField(
        db_index=True,
        help_text="Fixed deposit period start (interest accrual start).",
    )
    maturity_date = models.DateField(db_index=True)

    interest_rate = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        default=Decimal("25"),
        help_text="Nominal annual interest rate (%).",
    )
    interest_method = models.CharField(
        max_length=20,
        choices=InterestMethod.choices,
        default=InterestMethod.COMPOUND,
    )
    compounding_frequency = models.CharField(
        max_length=20,
        choices=CompoundingFrequency.choices,
        default=CompoundingFrequency.ANNUALLY,
        help_text="Used when interest method is compound.",
    )

    payout_structure_display = models.CharField(
        max_length=160,
        blank=True,
        default="At maturity",
        help_text="Short label shown on the member dashboard.",
    )

    tax_rate = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        default=Decimal("15"),
        help_text="Withholding on interest (% of gross). Used internally at withdrawal; not shown on member dashboard.",
    )

    auto_renewal = models.BooleanField(default=False)
    minimum_lock_period_days = models.PositiveIntegerField(
        default=0,
        help_text="Minimum days before early withdrawal (policy / internal).",
    )
    early_withdrawal_penalty = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        default=Decimal("0"),
        help_text="Penalty as % (policy / internal).",
    )

    notes = models.TextField(blank=True, help_text="Internal admin notes.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date", "-pk"]
        verbose_name = "GWC fixed deposit"
        verbose_name_plural = "GWC fixed deposits"
        indexes = [
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self) -> str:
        ref = self.deposit_id or f"#{self.pk or 'new'}"
        return f"{ref} — {self.user} ({self.status})"

    def clean(self) -> None:
        if self.start_date and self.maturity_date and self.maturity_date <= self.start_date:
            raise ValidationError({"maturity_date": "Maturity must be after start date."})
        if self.interest_method == self.InterestMethod.COMPOUND and not self.compounding_frequency:
            raise ValidationError(
                {"compounding_frequency": "Select a compounding frequency for compound interest."}
            )

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if not self.deposit_id:
            year = self.start_date.year if self.start_date else timezone.now().year
            new_id = f"GWC-{year}-{self.pk:05d}"
            GWCFixedDeposit.objects.filter(pk=self.pk).update(deposit_id=new_id)
            self.deposit_id = new_id
        if is_new and not self.activities.filter(description="Deposit funded").exists():
            GWCDepositActivity.objects.create(
                deposit=self,
                description="Deposit funded",
                activity_type=GWCDepositActivity.ActivityType.CREDIT,
                amount=self.principal_amount,
                timestamp=timezone.now(),
            )
