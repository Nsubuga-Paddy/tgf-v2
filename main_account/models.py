"""
Main Account — a unified MCS "bank" balance for each member.

Design:
- MainAccountTransaction is an append-only ledger of COMPLETED movements
  (credits and debits). Each row stores balance_after so history is auditable
  and the balance is always reconstructable.
- MainAccountWithdrawal is a withdrawal REQUEST (pending -> approved/rejected).
  Pending withdrawals reduce the "available" balance (funds are withheld).
  On approval, a debit transaction is posted to the ledger.

Funds flow IN from matured projects (member-initiated transfer to main account,
no admin approval) and admin credits. Funds flow OUT via withdrawals to bank
(admin-approved) and investments back into projects.

Project refund requests (e.g. Real Estate) are the project-side exception that
still require administrator approval before crediting Main Account.
"""
from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class MainAccountTransaction(models.Model):
    """Append-only ledger entry for a member's main account."""

    class Direction(models.TextChoices):
        CREDIT = "credit", "Credit (money in)"
        DEBIT = "debit", "Debit (money out)"

    class Category(models.TextChoices):
        OPENING_BALANCE = "opening_balance", "Opening balance"
        ADMIN_CREDIT = "admin_credit", "Admin credit"
        PROJECT_TRANSFER_IN = "project_transfer_in", "Transfer from project"
        DIVIDEND = "dividend", "Dividend payout"
        PROJECT_INVESTMENT = "project_investment", "Investment into project"
        WITHDRAWAL = "withdrawal", "Withdrawal to bank"
        ADJUSTMENT = "adjustment", "Adjustment / correction"

    user_profile = models.ForeignKey(
        "accounts.UserProfile",
        on_delete=models.CASCADE,
        related_name="main_account_transactions",
    )
    direction = models.CharField(max_length=10, choices=Direction.choices)
    category = models.CharField(max_length=30, choices=Category.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    balance_after = models.DecimalField(max_digits=14, decimal_places=2)

    # e.g. "Commercial Goat Farming", "Centenary Bank ****4021", "Staff allowance"
    source_label = models.CharField(max_length=160, blank=True)
    reference = models.CharField(max_length=40, unique=True, db_index=True)
    description = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posted_main_account_transactions",
        help_text="Admin/user who posted this entry (blank for system).",
    )
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "Main account transaction"
        verbose_name_plural = "Main account transactions"
        indexes = [
            models.Index(fields=["user_profile", "-created_at"], name="idx_matx_profile_time"),
        ]

    def __str__(self) -> str:
        sign = "+" if self.direction == self.Direction.CREDIT else "-"
        return f"{self.user_profile} {sign}{self.amount} ({self.get_category_display()})"

    @property
    def signed_amount(self) -> Decimal:
        if self.direction == self.Direction.CREDIT:
            return self.amount
        return -self.amount


class AdminMainAccountCredit(MainAccountTransaction):
    """Proxy used only in Django admin for a clear 'Credit member' workflow."""

    class Meta:
        proxy = True
        verbose_name = "Credit member main account"
        verbose_name_plural = "Credit member main account"


class ProjectTransferToMainAccount(MainAccountTransaction):
    """
    Proxy for admin audit of completed project → Main Account credits.

    These are member-initiated matured transfers (52WSC, CGF, etc.) and do not
    require administrator approval. Staff use this list for visibility only.
    """

    class Meta:
        proxy = True
        verbose_name = "Project transfer to main account"
        verbose_name_plural = "Project transfers to main account"


class MainAccountWithdrawal(models.Model):
    """A withdrawal request from the main account to the member's bank."""

    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_REVERSED = "reversed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_REVERSED, "Reversed"),
    ]

    PAYOUT_MOBILE_MONEY = "mobile_money"
    PAYOUT_BANK = "bank"
    PAYOUT_CHOICES = [
        (PAYOUT_MOBILE_MONEY, "Mobile money"),
        (PAYOUT_BANK, "Bank account"),
    ]

    user_profile = models.ForeignKey(
        "accounts.UserProfile",
        on_delete=models.CASCADE,
        related_name="main_account_withdrawals",
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    reason = models.TextField(blank=True)
    payout_method = models.CharField(
        max_length=20,
        choices=PAYOUT_CHOICES,
        default=PAYOUT_BANK,
        help_text="Where the member asked funds to be sent.",
    )
    payout_destination = models.CharField(
        max_length=255,
        blank=True,
        help_text="Snapshot of mobile number or bank details at request time.",
    )
    funding_note = models.TextField(
        blank=True,
        help_text=(
            "Snapshot of Main Account credits from projects/dividends at request time, "
            "so approvers can see where the member's funds came from."
        ),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    admin_notes = models.TextField(blank=True)

    # Set when approved and the debit ledger entry has been posted.
    transaction = models.OneToOneField(
        MainAccountTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="withdrawal",
    )
    reversal_transaction = models.OneToOneField(
        MainAccountTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reversed_withdrawal",
        help_text="Credit transaction posted when an approved withdrawal is reversed.",
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processed_main_account_withdrawals",
    )
    reversed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reversed_main_account_withdrawals",
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    reversed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Main account withdrawal"
        verbose_name_plural = "Main account withdrawals"

    def __str__(self) -> str:
        return f"{self.user_profile} withdraw {self.amount} ({self.get_status_display()})"


class ProjectTransferRequest(models.Model):
    """Legacy request-to-approve model for project → Main Account transfers.

    Matured project transfers are now member-initiated and post immediately via
    transfer_from_project (no admin approval). This model is retained for
    historical rows only. New matured flows must not create pending requests.
    """

    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

    user_profile = models.ForeignKey(
        "accounts.UserProfile",
        on_delete=models.CASCADE,
        related_name="project_transfer_requests",
    )
    project_label = models.CharField(
        max_length=160, help_text="Source project, e.g. 'Commercial Goat Farming'."
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    member_notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    admin_notes = models.TextField(blank=True)

    transaction = models.OneToOneField(
        MainAccountTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="project_transfer",
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processed_project_transfers",
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Legacy project transfer request"
        verbose_name_plural = "Legacy project transfer requests"

    def __str__(self) -> str:
        return f"{self.user_profile}: {self.project_label} -> main ({self.get_status_display()})"
