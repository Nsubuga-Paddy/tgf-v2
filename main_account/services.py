"""Service functions for the main account ledger.

All balance-mutating operations go through post_transaction() inside an atomic
block so balance_after is always consistent, even under concurrent posts.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import (
    MainAccountTransaction,
    MainAccountWithdrawal,
    ProjectTransferRequest,
)

TWO_PLACES = Decimal("0.01")
ZERO = Decimal("0.00")


def _q(amount) -> Decimal:
    return Decimal(amount or 0).quantize(TWO_PLACES)


def generate_reference(prefix: str = "TX") -> str:
    """Human-friendly unique reference, e.g. TX-9F3A2B7C."""
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def posted_balance(profile) -> Decimal:
    """Current ledger balance (sum of credits minus debits)."""
    latest = (
        MainAccountTransaction.objects.filter(user_profile=profile)
        .order_by("-created_at", "-id")
        .first()
    )
    if latest is not None:
        return _q(latest.balance_after)
    return ZERO


def pending_withdrawal_total(profile) -> Decimal:
    total = (
        MainAccountWithdrawal.objects.filter(
            user_profile=profile, status=MainAccountWithdrawal.STATUS_PENDING
        ).aggregate(t=Sum("amount"))["t"]
        or ZERO
    )
    return _q(total)


def available_balance(profile) -> Decimal:
    """Balance the member can actually withdraw right now."""
    available = posted_balance(profile) - pending_withdrawal_total(profile)
    return available if available > ZERO else ZERO


@transaction.atomic
def post_transaction(
    profile,
    *,
    direction: str,
    category: str,
    amount,
    source_label: str = "",
    description: str = "",
    created_by=None,
    reference_prefix: str = "TX",
) -> MainAccountTransaction:
    """Post a completed credit/debit entry and update the running balance."""
    amount = _q(amount)
    if amount <= ZERO:
        raise ValueError("Transaction amount must be positive.")

    # Lock this member's rows to serialize balance computation.
    locked = list(
        MainAccountTransaction.objects.select_for_update()
        .filter(user_profile=profile)
        .order_by("-created_at", "-id")[:1]
    )
    current = _q(locked[0].balance_after) if locked else ZERO

    if direction == MainAccountTransaction.Direction.CREDIT:
        new_balance = current + amount
    else:
        new_balance = current - amount

    return MainAccountTransaction.objects.create(
        user_profile=profile,
        direction=direction,
        category=category,
        amount=amount,
        balance_after=new_balance,
        source_label=source_label,
        description=description,
        created_by=created_by,
        reference=generate_reference(reference_prefix),
    )


def credit_member(profile, amount, *, source_label="", description="", created_by=None):
    """Admin credit (e.g. staff allowance, correction)."""
    return post_transaction(
        profile,
        direction=MainAccountTransaction.Direction.CREDIT,
        category=MainAccountTransaction.Category.ADMIN_CREDIT,
        amount=amount,
        source_label=source_label or "Admin credit",
        description=description,
        created_by=created_by,
        reference_prefix="CR",
    )


def transfer_from_project(profile, project_label, amount, *, description="", created_by=None):
    """Credit matured project funds into the main account."""
    return post_transaction(
        profile,
        direction=MainAccountTransaction.Direction.CREDIT,
        category=MainAccountTransaction.Category.PROJECT_TRANSFER_IN,
        amount=amount,
        source_label=project_label,
        description=description or f"Transfer from {project_label}",
        created_by=created_by,
        reference_prefix="TRF",
    )


def record_dividend(profile, amount, *, description="", created_by=None):
    """Credit a cooperative dividend payout into the main account."""
    return post_transaction(
        profile,
        direction=MainAccountTransaction.Direction.CREDIT,
        category=MainAccountTransaction.Category.DIVIDEND,
        amount=amount,
        source_label="Cooperative dividend",
        description=description or "Dividend payout",
        created_by=created_by,
        reference_prefix="DIV",
    )


def invest_to_project(profile, project_label, amount, *, description="", created_by=None):
    """Debit the main account to fund a project investment."""
    if _q(amount) > available_balance(profile):
        raise ValueError("Insufficient available balance for this investment.")
    return post_transaction(
        profile,
        direction=MainAccountTransaction.Direction.DEBIT,
        category=MainAccountTransaction.Category.PROJECT_INVESTMENT,
        amount=amount,
        source_label=project_label,
        description=description or f"Investment into {project_label}",
        created_by=created_by,
        reference_prefix="INV",
    )


def _payout_destination(profile, payout_method: str) -> str:
    if payout_method == MainAccountWithdrawal.PAYOUT_MOBILE_MONEY:
        number = str(profile.whatsapp_number or "").strip()
        if not number:
            raise ValueError("Add your mobile money / WhatsApp number on your profile before withdrawing.")
        return f"Mobile money: {number}"
    bank = (profile.bank_name or "").strip()
    acct = (profile.bank_account_number or "").strip()
    name = (profile.bank_account_name or "").strip()
    if not (bank and acct and name):
        raise ValueError("Add your full bank account details on your profile before withdrawing.")
    return f"{bank} · {acct} · {name}"


def create_withdrawal(
    profile,
    amount,
    *,
    reason="",
    payout_method=MainAccountWithdrawal.PAYOUT_BANK,
) -> MainAccountWithdrawal:
    """Create a pending withdrawal request; funds are withheld until decided."""
    amount = _q(amount)
    if amount <= ZERO:
        raise ValueError("Withdrawal amount must be positive.")
    if amount > available_balance(profile):
        raise ValueError("Insufficient available balance.")
    method = payout_method or MainAccountWithdrawal.PAYOUT_BANK
    if method not in {
        MainAccountWithdrawal.PAYOUT_MOBILE_MONEY,
        MainAccountWithdrawal.PAYOUT_BANK,
    }:
        raise ValueError("Choose mobile money or bank account as the payout destination.")
    destination = _payout_destination(profile, method)
    return MainAccountWithdrawal.objects.create(
        user_profile=profile,
        amount=amount,
        reason=reason,
        payout_method=method,
        payout_destination=destination,
        status=MainAccountWithdrawal.STATUS_PENDING,
    )


@transaction.atomic
def approve_withdrawal(withdrawal: MainAccountWithdrawal, *, admin=None, admin_notes=""):
    """Approve a pending withdrawal and post the debit to the ledger."""
    if withdrawal.status != MainAccountWithdrawal.STATUS_PENDING:
        raise ValueError("Only pending withdrawals can be approved.")
    source_label = (
        withdrawal.payout_destination
        or _bank_label(withdrawal.user_profile)
        or withdrawal.get_payout_method_display()
    )
    description = withdrawal.reason or (
        "Withdrawal to mobile money"
        if withdrawal.payout_method == MainAccountWithdrawal.PAYOUT_MOBILE_MONEY
        else "Withdrawal to bank"
    )
    tx = post_transaction(
        withdrawal.user_profile,
        direction=MainAccountTransaction.Direction.DEBIT,
        category=MainAccountTransaction.Category.WITHDRAWAL,
        amount=withdrawal.amount,
        source_label=source_label,
        description=description,
        created_by=admin,
        reference_prefix="WD",
    )
    withdrawal.status = MainAccountWithdrawal.STATUS_APPROVED
    withdrawal.transaction = tx
    withdrawal.processed_by = admin
    withdrawal.admin_notes = admin_notes
    withdrawal.processed_at = timezone.now()
    withdrawal.save()
    return withdrawal


def reject_withdrawal(withdrawal: MainAccountWithdrawal, *, admin=None, admin_notes=""):
    if withdrawal.status != MainAccountWithdrawal.STATUS_PENDING:
        raise ValueError("Only pending withdrawals can be rejected.")
    withdrawal.status = MainAccountWithdrawal.STATUS_REJECTED
    withdrawal.processed_by = admin
    withdrawal.admin_notes = admin_notes
    withdrawal.processed_at = timezone.now()
    withdrawal.save()
    return withdrawal


@transaction.atomic
def reverse_withdrawal(withdrawal: MainAccountWithdrawal, *, admin=None, admin_notes=""):
    """Reverse an approved withdrawal by posting an equal credit adjustment.

    The original debit ledger row remains untouched for audit history. The
    reversal credit restores the member's balance and is linked back to the
    approved withdrawal.
    """
    if withdrawal.status != MainAccountWithdrawal.STATUS_APPROVED:
        raise ValueError("Only approved withdrawals can be reversed.")
    if withdrawal.reversal_transaction_id:
        raise ValueError("This withdrawal has already been reversed.")

    original_ref = withdrawal.transaction.reference if withdrawal.transaction_id else "unknown"
    reason = (admin_notes or "").strip()
    description = f"Reversal of withdrawal {original_ref}."
    if reason:
        description += f" Reason: {reason}"

    tx = post_transaction(
        withdrawal.user_profile,
        direction=MainAccountTransaction.Direction.CREDIT,
        category=MainAccountTransaction.Category.ADJUSTMENT,
        amount=withdrawal.amount,
        source_label=f"Withdrawal reversal {original_ref}",
        description=description,
        created_by=admin,
        reference_prefix="REV",
    )
    withdrawal.status = MainAccountWithdrawal.STATUS_REVERSED
    withdrawal.reversal_transaction = tx
    withdrawal.reversed_by = admin
    withdrawal.admin_notes = reason or withdrawal.admin_notes
    withdrawal.reversed_at = timezone.now()
    withdrawal.save()
    return withdrawal


def create_transfer_request(profile, project_label, amount, *, member_notes="") -> ProjectTransferRequest:
    """Member requests to move matured project funds into the main account."""
    amount = _q(amount)
    if amount <= ZERO:
        raise ValueError("Transfer amount must be positive.")
    return ProjectTransferRequest.objects.create(
        user_profile=profile,
        project_label=project_label,
        amount=amount,
        member_notes=member_notes,
        status=ProjectTransferRequest.STATUS_PENDING,
    )


@transaction.atomic
def approve_transfer_request(req: ProjectTransferRequest, *, admin=None, admin_notes=""):
    if req.status != ProjectTransferRequest.STATUS_PENDING:
        raise ValueError("Only pending transfers can be approved.")
    tx = transfer_from_project(
        req.user_profile, req.project_label, req.amount, created_by=admin
    )
    req.status = ProjectTransferRequest.STATUS_APPROVED
    req.transaction = tx
    req.processed_by = admin
    req.admin_notes = admin_notes
    req.processed_at = timezone.now()
    req.save()
    return req


def reject_transfer_request(req: ProjectTransferRequest, *, admin=None, admin_notes=""):
    if req.status != ProjectTransferRequest.STATUS_PENDING:
        raise ValueError("Only pending transfers can be rejected.")
    req.status = ProjectTransferRequest.STATUS_REJECTED
    req.processed_by = admin
    req.admin_notes = admin_notes
    req.processed_at = timezone.now()
    req.save()
    return req


def _bank_label(profile) -> str:
    bank = (profile.bank_name or "").strip()
    acct = (profile.bank_account_number or "").strip()
    if bank and acct:
        return f"{bank} ****{acct[-4:]}"
    return bank or "Bank account"


def recent_transactions(profile, limit: int = 50):
    return list(
        MainAccountTransaction.objects.filter(user_profile=profile)[:limit]
    )
