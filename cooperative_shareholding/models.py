from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum


class CooperativeGlobalDefaults(models.Model):
    """Singleton: values that rarely change (reinvest price, Blue Diamond threshold)."""

    reinvest_share_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("1000000"),
        help_text="Price per share when reinvesting dividends (separate from cooperative book).",
    )
    blue_diamond_usd_threshold = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("1000000"),
        help_text="USD equivalent for Blue Diamond tier.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cooperative global defaults"
        verbose_name_plural = "Cooperative global defaults"

    def save(self, *args, **kwargs):
        self.pk = self.pk or 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls) -> CooperativeGlobalDefaults:
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class CooperativeIssuancePeriod(models.Model):
    """
    Admin can add multiple rows (e.g. per dividend issuance) when USD/UGX rate changes.
    Linked from each member shareholding record.
    """

    name = models.CharField(
        max_length=120,
        help_text="Label, e.g. 'December 2025 dividend issuance'.",
    )
    usd_to_ugx_rate = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("3800"),
        help_text="USD to UGX rate for this issuance period.",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Issuance period (USD rate)"
        verbose_name_plural = "Issuance periods (USD rates)"

    def __str__(self) -> str:
        return f"{self.name} — UGX {self.usd_to_ugx_rate:,.2f} per USD"


class CooperativeShareholding(models.Model):
    """Per-member cooperative holdings (admin-maintained)."""

    class CertificateStatus(models.TextChoices):
        ISSUED = "issued", "Issued"
        PENDING = "pending", "Pending"
        NOT_ISSUED = "not_issued", "Not issued"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cooperative_shareholding",
    )
    year_joined = models.PositiveSmallIntegerField(null=True, blank=True)
    certificate_status = models.CharField(
        max_length=20,
        choices=CertificateStatus.choices,
        default=CertificateStatus.PENDING,
        blank=True,
    )
    current_share_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("100000"),
        help_text="Current cooperative share price in UGX for this member.",
    )
    dividend_rate = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        default=Decimal("0.26"),
        help_text="Dividend rate as decimal (0.26 = 26%).",
    )
    dividend_election_open = models.BooleanField(
        default=False,
        help_text="When enabled, this member can submit a dividend payout choice.",
    )
    issuance_period = models.ForeignKey(
        CooperativeIssuancePeriod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shareholdings",
        help_text="USD rate period for Blue Diamond tier (optional).",
    )
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cooperative shareholding"
        verbose_name_plural = "Cooperative shareholdings"

    def __str__(self) -> str:
        return self.user.get_full_name() or self.user.get_username()

    @property
    def total_shares(self) -> int:
        return int(
            self.acquisition_lines.filter(shares_held__gt=0).aggregate(t=Sum("shares_held"))[
                "t"
            ]
            or 0
        )

    @property
    def usd_to_ugx_rate(self) -> Decimal:
        if self.issuance_period_id:
            return self.issuance_period.usd_to_ugx_rate
        return Decimal("3800")


class ShareAcquisitionLine(models.Model):
    shareholding = models.ForeignKey(
        CooperativeShareholding,
        on_delete=models.CASCADE,
        related_name="acquisition_lines",
    )
    receipt_number = models.CharField(max_length=64, blank=True)
    acquisition_date = models.DateField(null=True, blank=True)
    shares_held = models.PositiveIntegerField(default=0)
    share_amount = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=Decimal("0"),
    )
    price_per_share = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )
    source_description = models.CharField(
        max_length=255,
        blank=True,
        help_text="e.g. dividend reinvestment choice, manual purchase.",
    )

    class Meta:
        ordering = ["-acquisition_date", "-pk"]
        verbose_name = "Share acquisition line"
        verbose_name_plural = "Share acquisition lines"

    def __str__(self) -> str:
        return f"{self.receipt_number or '—'}: {self.shares_held} shares"


MESU_SHARE_PRICE = Decimal("1000000")


class DividendChoiceRequest(models.Model):
    """One member submission per dividend request (may split across channels)."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        PROCESSED = "processed", "Processed"

    shareholding = models.ForeignKey(
        CooperativeShareholding,
        on_delete=models.CASCADE,
        related_name="dividend_choices",
    )
    total_dividend = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        help_text="Expected dividend at time of submission.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    member_notes = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    ledger_applied_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When approved allocations were posted to acquisitions / related ledgers.",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Dividend request submission"
        verbose_name_plural = "Dividend request submissions"

    def __str__(self) -> str:
        return f"{self.shareholding} — UGX {self.total_dividend:,.0f} ({self.get_status_display()})"

    @property
    def allocation_summary(self) -> str:
        parts = []
        for line in self.allocation_lines.all():
            parts.append(f"{line.get_action_type_display()}: UGX {line.amount:,.0f}")
        return "; ".join(parts) if parts else "—"


class DividendAllocationLine(models.Model):
    class ActionType(models.TextChoices):
        CASH = "cash", "Cash (MoMo / bank)"
        MCS_SHARES = "mcs_shares", "MCS cooperative shares (UGX 1M/share)"
        MESU_SHARES = "mesu_shares", "MESU Academy shares (UGX 1M/share)"
        SAVINGS = "savings", "MCS Fixed Savings (7.5% p.a.)"

    submission = models.ForeignKey(
        DividendChoiceRequest,
        on_delete=models.CASCADE,
        related_name="allocation_lines",
    )
    action_type = models.CharField(max_length=20, choices=ActionType.choices)
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    shares_count = models.PositiveIntegerField(
        default=0,
        help_text="Whole shares for MCS/MESU reinvestment lines.",
    )

    class Meta:
        ordering = ["action_type"]
        verbose_name = "Dividend allocation line"
        verbose_name_plural = "Dividend allocation lines"

    def __str__(self) -> str:
        extra = f" ({self.shares_count} shares)" if self.shares_count else ""
        return f"{self.get_action_type_display()}: UGX {self.amount:,.0f}{extra}"


class DividendDisbursement(models.Model):
    """Records dividend paid out or reinvested when a request is approved."""

    class FulfillmentType(models.TextChoices):
        CASH_PAID = "cash_paid", "Cash paid (MoMo / bank)"
        MCS_REINVEST = "mcs_reinvest", "Reinvested in MCS shares"
        MESU_REINVEST = "mesu_reinvest", "Reinvested in MESU Academy shares"
        SAVINGS_DEPOSIT = "savings_deposit", "Fixed / compulsory deposit"

    shareholding = models.ForeignKey(
        CooperativeShareholding,
        on_delete=models.CASCADE,
        related_name="dividend_disbursements",
    )
    submission = models.ForeignKey(
        DividendChoiceRequest,
        on_delete=models.CASCADE,
        related_name="disbursements",
    )
    allocation_line = models.OneToOneField(
        DividendAllocationLine,
        on_delete=models.CASCADE,
        related_name="disbursement",
    )
    fulfillment_type = models.CharField(max_length=20, choices=FulfillmentType.choices)
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    shares_count = models.PositiveIntegerField(default=0)
    disbursed_at = models.DateTimeField()
    payment_reference = models.CharField(
        max_length=120,
        blank=True,
        help_text="MoMo / bank reference when paid manually.",
    )
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-disbursed_at", "-pk"]
        verbose_name = "Dividend disbursement"
        verbose_name_plural = "Dividend disbursements"

    def __str__(self) -> str:
        return f"{self.get_fulfillment_type_display()} — UGX {self.amount:,.0f}"
