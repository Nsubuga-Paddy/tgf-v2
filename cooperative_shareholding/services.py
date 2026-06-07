from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import (
    CooperativeGlobalDefaults,
    CooperativeShareholding,
    DividendAllocationLine,
    DividendChoiceRequest,
    DividendDisbursement,
    ShareAcquisitionLine,
)

PROJECT_NAME = "Cooperative Shareholding"

TIER_EMOJIS = {
    "Standard": "🌱",
    "Elite": "⭐",
    "Gold": "🥇",
    "Platinum": "🏆",
    "Diamond": "💎",
    "Blue Diamond": "💙💎",
}


def get_tier_emoji(tier_name: str) -> str:
    return TIER_EMOJIS.get(tier_name, "")


def get_shareholder_tier(
    total_shares: int,
    current_value_ugx: Decimal,
    usd_to_ugx_rate: Decimal,
    global_defaults: CooperativeGlobalDefaults | None = None,
) -> str:
    global_defaults = global_defaults or CooperativeGlobalDefaults.get_solo()
    blue_ugx = global_defaults.blue_diamond_usd_threshold * usd_to_ugx_rate
    if current_value_ugx >= blue_ugx:
        return "Blue Diamond"
    if total_shares >= 2000:
        return "Diamond"
    if total_shares >= 1000:
        return "Platinum"
    if total_shares >= 500:
        return "Gold"
    if total_shares >= 100:
        return "Elite"
    return "Standard"


def build_shareholding_summary(
    shareholding: CooperativeShareholding,
) -> dict[str, Any]:
    global_defaults = CooperativeGlobalDefaults.get_solo()
    lines = shareholding.acquisition_lines.filter(shares_held__gt=0)
    total_shares = int(lines.aggregate(t=Sum("shares_held"))["t"] or 0)
    total_historical = lines.aggregate(t=Sum("share_amount"))["t"] or Decimal("0")
    current_share_price = shareholding.current_share_price
    current_share_value = Decimal(total_shares) * current_share_price
    usd_rate = shareholding.usd_to_ugx_rate
    tier = get_shareholder_tier(
        total_shares, current_share_value, usd_rate, global_defaults
    )
    expected_dividend = (
        current_share_value * shareholding.dividend_rate
    ).quantize(Decimal("1"))
    rate_pct = (shareholding.dividend_rate * 100).quantize(Decimal("0.01"))
    return {
        "total_shares": total_shares,
        "total_historical_amount": total_historical,
        "current_share_price": current_share_price,
        "current_share_value": current_share_value,
        "dividend_rate": shareholding.dividend_rate,
        "dividend_rate_percent": rate_pct,
        "expected_dividend": expected_dividend,
        "tier": tier,
        "tier_emoji": get_tier_emoji(tier),
        "year_joined": shareholding.year_joined,
        "certificate_status": shareholding.get_certificate_status_display(),
        "reinvest_share_price": global_defaults.reinvest_share_price,
        "usd_to_ugx_rate": usd_rate,
        "issuance_period_name": (
            shareholding.issuance_period.name
            if shareholding.issuance_period_id
            else None
        ),
    }


def user_has_cooperative_access(profile) -> bool:
    return profile.projects.filter(name=PROJECT_NAME).exists()


ALLOCATION_POST_KEYS = {
    DividendAllocationLine.ActionType.CASH: "alloc_cash",
    DividendAllocationLine.ActionType.MCS_SHARES: "alloc_mcs_shares",
    DividendAllocationLine.ActionType.SAVINGS: "alloc_savings",
}


def _parse_ugx_amount(raw: str) -> Decimal:
    cleaned = (raw or "").strip().replace(",", "")
    if not cleaned:
        return Decimal("0")
    return Decimal(cleaned).quantize(Decimal("1"))


def parse_dividend_allocations_from_post(post_data) -> list[tuple[str, Decimal]]:
    """Return (action_type, amount) pairs with amount > 0."""
    lines = []
    for action_type, field_name in ALLOCATION_POST_KEYS.items():
        amount = _parse_ugx_amount(post_data.get(field_name, ""))
        if amount > 0:
            lines.append((action_type, amount))
    return lines


def validate_dividend_allocations(
    allocations: list[tuple[str, Decimal]],
    expected_total: Decimal,
) -> str | None:
    """Return an error message, or None if valid."""
    if not allocations:
        return "Allocate at least one portion of your dividend."
    for _action, amount in allocations:
        if amount < 0:
            return "Amounts cannot be negative."
    total = sum((a for _, a in allocations), Decimal("0"))
    if total != expected_total:
        return (
            f"Your allocations must add up to UGX {expected_total:,.0f}. "
            f"You entered UGX {total:,.0f}."
        )
    return None


def shares_for_amount(amount: Decimal, price_per_share: Decimal) -> int:
    if price_per_share <= 0:
        return 0
    return int(amount // price_per_share)


def _allocation_line_models(
    submission: DividendChoiceRequest,
    allocations: list[tuple[str, Decimal]],
) -> list[DividendAllocationLine]:
    global_defaults = CooperativeGlobalDefaults.get_solo()
    mcs_price = global_defaults.reinvest_share_price
    line_models = []
    for action_type, amount in allocations:
        shares_count = 0
        if action_type == DividendAllocationLine.ActionType.MCS_SHARES:
            shares_count = shares_for_amount(amount, mcs_price)
        line_models.append(
            DividendAllocationLine(
                submission=submission,
                action_type=action_type,
                amount=amount,
                shares_count=shares_count,
            )
        )
    return line_models


def submission_is_editable_by_member(submission: DividendChoiceRequest) -> bool:
    return submission.status == DividendChoiceRequest.Status.PENDING


def build_pending_edit_payload(submission: DividendChoiceRequest) -> dict[str, Any]:
    """Amounts per channel for pre-filling the profile edit form."""
    amounts = {
        DividendAllocationLine.ActionType.CASH: 0,
        DividendAllocationLine.ActionType.MCS_SHARES: 0,
        DividendAllocationLine.ActionType.SAVINGS: 0,
    }
    for line in submission.allocation_lines.all():
        amounts[line.action_type] = int(line.amount)
    return {
        "submission_id": submission.pk,
        "alloc_cash": amounts[DividendAllocationLine.ActionType.CASH],
        "alloc_mcs_shares": amounts[DividendAllocationLine.ActionType.MCS_SHARES],
        "alloc_savings": amounts[DividendAllocationLine.ActionType.SAVINGS],
        "notes": submission.member_notes or "",
    }


def create_dividend_submission(
    shareholding: CooperativeShareholding,
    expected_total: Decimal,
    allocations: list[tuple[str, Decimal]],
    member_notes: str = "",
) -> DividendChoiceRequest:
    submission = DividendChoiceRequest.objects.create(
        shareholding=shareholding,
        total_dividend=expected_total,
        member_notes=member_notes,
        status=DividendChoiceRequest.Status.PENDING,
    )
    DividendAllocationLine.objects.bulk_create(
        _allocation_line_models(submission, allocations)
    )
    return submission


def update_dividend_submission(
    submission: DividendChoiceRequest,
    expected_total: Decimal,
    allocations: list[tuple[str, Decimal]],
    member_notes: str = "",
) -> DividendChoiceRequest:
    if not submission_is_editable_by_member(submission):
        raise ValueError("This dividend request can no longer be edited.")
    submission.total_dividend = expected_total
    submission.member_notes = member_notes
    submission.save(update_fields=["total_dividend", "member_notes"])
    submission.allocation_lines.all().delete()
    DividendAllocationLine.objects.bulk_create(
        _allocation_line_models(submission, allocations)
    )
    return submission


def _fulfillment_type_for_line(line: DividendAllocationLine) -> str:
    mapping = {
        DividendAllocationLine.ActionType.CASH: DividendDisbursement.FulfillmentType.CASH_PAID,
        DividendAllocationLine.ActionType.MCS_SHARES: DividendDisbursement.FulfillmentType.MCS_REINVEST,
        DividendAllocationLine.ActionType.SAVINGS: DividendDisbursement.FulfillmentType.SAVINGS_DEPOSIT,
    }
    return mapping[line.action_type]


def build_dividend_account_summary(shareholding: CooperativeShareholding) -> dict[str, Any]:
    """Member-facing dividend entitlement vs amounts already disbursed."""
    holding_summary = build_shareholding_summary(shareholding)
    expected = holding_summary["expected_dividend"]

    disbursements = list(
        DividendDisbursement.objects.filter(shareholding=shareholding).order_by(
            "-disbursed_at", "-pk"
        )
    )
    total_disbursed = sum((d.amount for d in disbursements), Decimal("0"))

    active_submission = (
        DividendChoiceRequest.objects.filter(shareholding=shareholding)
        .exclude(status=DividendChoiceRequest.Status.REJECTED)
        .order_by("-created_at")
        .first()
    )
    cycle_entitlement = (
        active_submission.total_dividend if active_submission else expected
    )
    if active_submission and active_submission.status in (
        DividendChoiceRequest.Status.APPROVED,
        DividendChoiceRequest.Status.PROCESSED,
    ):
        cycle_disbursed = total_disbursed
        outstanding = (cycle_entitlement - cycle_disbursed).quantize(Decimal("1"))
        if outstanding < 0:
            outstanding = Decimal("0")
    elif active_submission and active_submission.status == DividendChoiceRequest.Status.PENDING:
        cycle_disbursed = Decimal("0")
        outstanding = cycle_entitlement
    else:
        cycle_disbursed = total_disbursed
        outstanding = (expected - total_disbursed).quantize(Decimal("1"))
        if outstanding < 0:
            outstanding = Decimal("0")

    return {
        "expected_dividend": expected,
        "cycle_entitlement": cycle_entitlement,
        "total_disbursed": total_disbursed,
        "cycle_disbursed": cycle_disbursed,
        "outstanding_balance": outstanding,
        "disbursements": disbursements,
        "has_disbursements": bool(disbursements),
    }


@transaction.atomic
def apply_approved_dividend_ledger(submission: DividendChoiceRequest) -> None:
    """
    Fulfill an approved dividend request: record disbursements and add MCS
    cooperative shares to acquisitions where applicable.
    """
    if submission.ledger_applied_at:
        return
    if submission.status not in (
        DividendChoiceRequest.Status.APPROVED,
        DividendChoiceRequest.Status.PROCESSED,
    ):
        return

    shareholding = submission.shareholding
    global_defaults = CooperativeGlobalDefaults.get_solo()
    mcs_price = global_defaults.reinvest_share_price
    today = timezone.localdate()
    now = timezone.now()

    for line in submission.allocation_lines.all():
        fulfillment = _fulfillment_type_for_line(line)
        DividendDisbursement.objects.create(
            shareholding=shareholding,
            submission=submission,
            allocation_line=line,
            fulfillment_type=fulfillment,
            amount=line.amount,
            shares_count=line.shares_count or 0,
            disbursed_at=now,
            notes=line.get_action_type_display(),
        )

        if line.action_type == DividendAllocationLine.ActionType.MCS_SHARES:
            ShareAcquisitionLine.objects.create(
                shareholding=shareholding,
                receipt_number=f"DIV-{submission.pk}-MCS",
                acquisition_date=today,
                shares_held=line.shares_count or 0,
                share_amount=line.amount,
                price_per_share=mcs_price,
                source_description="Dividend reinvestment — MCS shares",
            )
    submission.ledger_applied_at = now
    submission.save(update_fields=["ledger_applied_at"])


def cooperative_display_state(profile, shareholding) -> str:
    """
    full — access + admin record with data shown
    pending_setup — access but no shareholding record yet
    no_access — no project access
    """
    if not user_has_cooperative_access(profile):
        return "no_access"
    if shareholding is None:
        return "pending_setup"
    return "full"
