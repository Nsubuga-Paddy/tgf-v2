from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from accounts.models import MemberNotification
from main_account import services as main_ledger

from .cycle_service import (
    CYCLE_WEEKS,
    TARGET_AMOUNT,
    active_cycle_for_progress,
    build_cycle_payload,
    cycle_deposit_total,
    sync_member_cycles,
)
from .models import SavingsCycle, SavingsTransaction

PROJECT_NAME = "52 Weeks Saving Challenge"
TWO_PLACES = Decimal("0.01")
ZERO = Decimal("0.00")


def _q(amount) -> Decimal:
    return Decimal(amount or 0).quantize(TWO_PLACES)


def _can_accept_contribution(profile) -> tuple[bool, str]:
    """
    Contributions need an active personal cycle, or a first-time open cycle.
    Matured cycles awaiting a member decision block new deposits.
    """
    active = active_cycle_for_progress(profile)
    if active:
        return True, ""
    pending = SavingsCycle.objects.filter(
        user_profile=profile,
        status__in=[
            SavingsCycle.STATUS_AWAITING_DECISION,
            SavingsCycle.STATUS_POT_AVAILABLE,
        ],
    ).exists()
    if pending:
        return False, (
            "Your previous 52WSC cycle has matured. Complete the next-step decision "
            "on the 52WSC page before contributing again."
        )
    return True, ""


def build_contribute_options(profile) -> dict[str, Any]:
    sync_member_cycles(profile)
    cycle_info = build_cycle_payload(profile, active_cycle_for_progress(profile))
    can_contribute, block_message = _can_accept_contribution(profile)
    available = main_ledger.available_balance(profile)
    cycle_deposits = int(cycle_info.get("cycleDeposits") or 0)
    target = int(TARGET_AMOUNT) if TARGET_AMOUNT else 13_780_000
    return {
        "availableMain": float(available),
        "targetAmount": target,
        "cycleDeposits": cycle_deposits,
        "progressPercentage": float(cycle_info.get("progressPercentage") or 0),
        "weeksCompleted": int(cycle_info.get("weeksCompleted") or 0),
        "nextWeekToCover": int(cycle_info.get("nextWeekToCover") or 1),
        "totalWeeks": CYCLE_WEEKS,
        "cycleLabel": cycle_info.get("cycleLabel"),
        "balanceBroughtForward": int(cycle_info.get("balanceBroughtForward") or 0),
        "canContribute": can_contribute,
        "blockMessage": block_message,
        "hasProjectAccess": bool(profile.has_project(PROJECT_NAME)),
    }


@transaction.atomic
def contribute_from_main_account(
    profile,
    amount,
    *,
    notes: str = "",
    created_by=None,
) -> dict[str, Any]:
    if not profile.has_project(PROJECT_NAME):
        raise ValueError("You do not have access to the 52 Weeks Saving Challenge.")

    amount = _q(amount)
    if amount <= ZERO:
        raise ValueError("Enter a valid contribution amount.")

    can_contribute, block_message = _can_accept_contribution(profile)
    if not can_contribute:
        raise ValueError(block_message)

    if amount > main_ledger.available_balance(profile):
        raise ValueError("Amount exceeds Main Account available balance.")

    note_text = (notes or "").strip()
    description = f"52WSC contribution of UGX {amount:,.0f} from Main Account."
    if note_text:
        description = f"{description} Note: {note_text}"

    main_tx = main_ledger.invest_to_project(
        profile,
        PROJECT_NAME,
        amount,
        description=description,
        created_by=created_by or profile.user,
    )

    deposit = SavingsTransaction(
        user_profile=profile,
        amount=amount,
        transaction_type="deposit",
        transaction_date=timezone.localdate(),
        receipt_number=main_tx.reference,
    )
    deposit.save()

    if deposit.cycle_id is None and active_cycle_for_progress(profile) is None:
        # Should be rare after pre-checks; fail closed so Main debit rolls back.
        raise ValueError(
            "Could not attach this contribution to an active 52WSC cycle. "
            "Please complete any matured-cycle decision first."
        )

    cycle = deposit.cycle or active_cycle_for_progress(profile)
    cycle_total = cycle_deposit_total(cycle) if cycle else amount
    MemberNotification.objects.create(
        user=profile.user,
        source=MemberNotification.Source.SYSTEM,
        title="52WSC contribution posted",
        body=(
            f"UGX {amount:,.0f} was moved from your Main Account into your "
            f"52 Weeks Saving Challenge. Receipt {main_tx.reference}."
        ),
    )
    return {
        "transaction": main_tx,
        "deposit": deposit,
        "amount": amount,
        "cycle_total": cycle_total,
        "receipt": main_tx.reference,
        "notes": note_text,
        "options": build_contribute_options(profile),
    }
