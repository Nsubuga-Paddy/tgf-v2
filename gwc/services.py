"""
Interest math, monthly redeem ledger, and dashboard DTOs for GWC fixed deposits.
"""
from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from math import pow
from typing import Any

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import GWCDepositActivity, GWCFixedDeposit, GWCInterestRedemption

Q2 = Decimal("0.01")
ZERO = Decimal("0.00")
PROJECT_LABEL = "Generational Wealth Creation"


def tenure_days(start: date, end: date) -> int:
    return max(1, (end - start).days)


def elapsed_days(start: date, maturity: date, as_of: date) -> int:
    if as_of < start:
        return 0
    cap = min(as_of, maturity)
    return max(0, (cap - start).days)


def periods_per_year(freq: str) -> int:
    return {"daily": 365, "monthly": 12, "quarterly": 4, "annually": 1}.get(freq or "", 12)


def gross_interest_simple(principal: Decimal, rate_pct: Decimal, days: int) -> Decimal:
    if days <= 0:
        return Decimal("0")
    return (
        principal * rate_pct / Decimal("100") * Decimal(days) / Decimal("365")
    ).quantize(Q2, ROUND_HALF_UP)


def gross_interest_compound(principal: Decimal, rate_pct: Decimal, n_per_year: int, days: int) -> Decimal:
    """Gross interest: A - P with A = P * (1 + r/n)^(n*t), t = days/365."""
    if days <= 0 or principal <= 0:
        return Decimal("0")
    n = max(1, n_per_year)
    years = float(Decimal(days) / Decimal("365"))
    r = float(rate_pct / Decimal("100"))
    base = 1 + r / n
    factor = Decimal(str(pow(base, n * years)))
    gross = principal * (factor - Decimal("1"))
    return gross.quantize(Q2, ROUND_HALF_UP)


def _gross_for_days(deposit: GWCFixedDeposit, days: int) -> Decimal:
    p = deposit.principal_amount
    r = deposit.interest_rate
    if deposit.interest_method == GWCFixedDeposit.InterestMethod.SIMPLE:
        return gross_interest_simple(p, r, days)
    n = periods_per_year(deposit.compounding_frequency)
    return gross_interest_compound(p, r, n, days)


def _net_of_tax(gross: Decimal, tax_rate: Decimal) -> Decimal:
    if gross <= 0:
        return ZERO
    tax = (gross * tax_rate / Decimal("100")).quantize(Q2, ROUND_HALF_UP)
    return (gross - tax).quantize(Q2, ROUND_HALF_UP)


def _month_last_day(year: int, month: int) -> date:
    return date(year, month, monthrange(year, month)[1])


def _add_month(year: int, month: int) -> tuple[int, int]:
    if month == 12:
        return year + 1, 1
    return year, month + 1


def completed_calendar_month_periods(
    start: date, maturity: date, as_of: date
) -> list[tuple[date, date, date]]:
    """
    Return (month_first, period_start, period_end) for each fully completed
    calendar month that overlaps the deposit term.

    A month is completed when as_of is strictly after that month's last day.
    """
    if not start or not maturity or as_of <= start:
        return []

    term_end = min(maturity, as_of)
    out: list[tuple[date, date, date]] = []
    y, m = start.year, start.month
    while True:
        month_first = date(y, m, 1)
        month_last = _month_last_day(y, m)
        if as_of <= month_last:
            break
        period_start = max(start, month_first)
        period_end = min(maturity, month_last)
        if period_start <= period_end and period_start <= term_end:
            out.append((month_first, period_start, period_end))
        y, m = _add_month(y, m)
        if month_first > maturity:
            break
    return out


def interest_for_date_range(deposit: GWCFixedDeposit, period_start: date, period_end: date) -> Decimal:
    """Net-of-tax interest for inclusive calendar days in [period_start, period_end]."""
    if period_end < period_start:
        return ZERO
    days = (period_end - period_start).days + 1
    gross = _gross_for_days(deposit, days)
    return _net_of_tax(gross, deposit.tax_rate)


def total_redeemed_interest(deposit: GWCFixedDeposit) -> Decimal:
    total = deposit.interest_redemptions.aggregate(t=Sum("amount"))["t"]
    if total is None:
        return ZERO
    return Decimal(total).quantize(Q2, ROUND_HALF_UP)


def monthly_interest_ledger(deposit: GWCFixedDeposit, as_of: date | None = None) -> dict[str, Any]:
    """
    Calendar-month interest ledger for a deposit.

    Redeemable only applies when redeemable_monthly_interest is enabled;
    ledger rows are still computed for visibility when the flag is on.
    """
    as_of = as_of or timezone.localdate()
    periods = completed_calendar_month_periods(deposit.start_date, deposit.maturity_date, as_of)
    rows: list[dict[str, Any]] = []
    total_earned = ZERO
    for month_first, period_start, period_end in periods:
        earned = interest_for_date_range(deposit, period_start, period_end)
        total_earned += earned
        rows.append(
            {
                "period_key": month_first.strftime("%Y-%m"),
                "period_label": month_first.strftime("%b %Y"),
                "period_start": period_start,
                "period_end": period_end,
                "earned": earned,
            }
        )

    redeemed = total_redeemed_interest(deposit)
    redeemable = max(ZERO, (total_earned - redeemed).quantize(Q2, ROUND_HALF_UP))
    can_redeem = bool(
        deposit.redeemable_monthly_interest
        and deposit.status
        in (GWCFixedDeposit.Status.ACTIVE, GWCFixedDeposit.Status.MATURED)
        and redeemable > ZERO
    )

    redemptions = [
        {
            "id": r.pk,
            "amount": r.amount,
            "redeemed_at": r.redeemed_at,
            "notes": r.notes or "",
            "reference": (
                r.main_account_transaction.reference
                if r.main_account_transaction_id
                else ""
            ),
        }
        for r in deposit.interest_redemptions.select_related(
            "main_account_transaction"
        ).order_by("-redeemed_at", "-pk")
    ]

    # Running redeemable after chronological earnings, then subtract redemptions in time order
    # for display: show earned per month; allocate withdrawals FIFO across months for "transferred" column.
    remaining_to_allocate = redeemed
    display_rows: list[dict[str, Any]] = []
    for row in rows:
        earned = row["earned"]
        transferred = min(earned, remaining_to_allocate)
        remaining_to_allocate = (remaining_to_allocate - transferred).quantize(Q2, ROUND_HALF_UP)
        display_rows.append(
            {
                "periodKey": row["period_key"],
                "periodLabel": row["period_label"],
                "earned": earned,
                "transferred": transferred,
                "carry": (earned - transferred).quantize(Q2, ROUND_HALF_UP),
            }
        )

    return {
        "enabled": bool(deposit.redeemable_monthly_interest),
        "total_earned": total_earned.quantize(Q2, ROUND_HALF_UP),
        "total_redeemed": redeemed,
        "redeemable": redeemable,
        "can_redeem": can_redeem,
        "months": display_rows,
        "redemptions": redemptions,
    }


@transaction.atomic
def transfer_redeemable_interest_to_main(
    deposit: GWCFixedDeposit,
    *,
    amount: Decimal | None = None,
    actor=None,
    notes: str = "",
) -> GWCInterestRedemption:
    """Credit Main Account with redeemable GWC interest (not principal)."""
    from main_account import services as main_account_ledger

    if not deposit.redeemable_monthly_interest:
        raise ValueError("Monthly interest redemption is not enabled for this deposit.")
    if deposit.status not in (
        GWCFixedDeposit.Status.ACTIVE,
        GWCFixedDeposit.Status.MATURED,
    ):
        raise ValueError("Only active or matured deposits can redeem interest.")

    ledger = monthly_interest_ledger(deposit)
    available = ledger["redeemable"]
    if available <= ZERO:
        raise ValueError("No redeemable interest available to transfer.")

    transfer_amount = available if amount is None else Decimal(str(amount)).quantize(
        Q2, ROUND_HALF_UP
    )
    if transfer_amount <= ZERO:
        raise ValueError("Transfer amount must be greater than zero.")
    if transfer_amount > available:
        raise ValueError(
            f"Amount exceeds redeemable interest (available UGX {available:,.0f})."
        )

    profile = deposit.user.profile
    now = timezone.now()
    note = (notes or "").strip() or (
        f"GWC monthly interest redeemed from {deposit.deposit_id} "
        f"(UGX {transfer_amount:,.0f})."
    )

    main_tx = main_account_ledger.transfer_from_project(
        profile,
        PROJECT_LABEL,
        transfer_amount,
        description=(
            f"GWC interest redemption · {deposit.deposit_id}: "
            f"UGX {transfer_amount:,.0f}"
        ),
        created_by=actor,
    )

    redemption = GWCInterestRedemption.objects.create(
        deposit=deposit,
        amount=transfer_amount,
        redeemed_at=now,
        notes=note,
        main_account_transaction=main_tx,
        created_by=actor,
    )

    GWCDepositActivity.objects.create(
        deposit=deposit,
        description="Interest transferred to Main Account",
        activity_type=GWCDepositActivity.ActivityType.DEBIT,
        amount=transfer_amount,
        timestamp=now,
    )

    return redemption


def deposit_to_display(deposit: GWCFixedDeposit, as_of: date | None = None) -> dict[str, Any]:
    """Build a dict matching gwc-dashboard.html deposit fields."""
    as_of = as_of or timezone.localdate()
    p = deposit.principal_amount
    r = deposit.interest_rate
    start = deposit.start_date
    mat = deposit.maturity_date
    total_days = tenure_days(start, mat)

    elapsed = elapsed_days(start, mat, as_of)
    if deposit.status == GWCFixedDeposit.Status.MATURED:
        elapsed = total_days
    elif deposit.status == GWCFixedDeposit.Status.WITHDRAWN:
        elapsed = min(elapsed, total_days)

    if deposit.interest_method == GWCFixedDeposit.InterestMethod.SIMPLE:
        gross_full = gross_interest_simple(p, r, total_days)
        gross_accrued = gross_interest_simple(p, r, elapsed)
    else:
        n = periods_per_year(deposit.compounding_frequency)
        gross_full = gross_interest_compound(p, r, n, total_days)
        gross_accrued = gross_interest_compound(p, r, n, elapsed)

    tax_rate = deposit.tax_rate
    tax_on_full = (gross_full * tax_rate / Decimal("100")).quantize(Q2, ROUND_HALF_UP)
    net_full = (gross_full - tax_on_full).quantize(Q2, ROUND_HALF_UP)
    projected_maturity = (p + net_full).quantize(Q2, ROUND_HALF_UP)

    if gross_full > 0:
        tax_accrued = (gross_accrued * tax_rate / Decimal("100")).quantize(Q2, ROUND_HALF_UP)
    else:
        tax_accrued = Decimal("0")
    accrued_interest = (gross_accrued - tax_accrued).quantize(Q2, ROUND_HALF_UP)

    daily_gross_avg = (gross_full / Decimal(total_days)).quantize(Q2, ROUND_HALF_UP)
    monthly_approx = (daily_gross_avg * Decimal("30")).quantize(Q2, ROUND_HALF_UP)

    completion = (Decimal("100") * Decimal(elapsed) / Decimal(total_days)).quantize(
        Decimal("1"), ROUND_HALF_UP
    )
    if completion > 100:
        completion = Decimal("100")
    completion_i = int(completion)

    remaining = max(0, total_days - elapsed)
    days_to_mat = (mat - as_of).days
    is_upcoming = (
        deposit.status == GWCFixedDeposit.Status.ACTIVE and 0 <= days_to_mat <= 30
    )

    interest_ledger = monthly_interest_ledger(deposit, as_of=as_of)

    return {
        "deposit_id": deposit.deposit_id,
        "pk": deposit.pk,
        "status": deposit.status,
        "is_upcoming": is_upcoming,
        "principal_amount": p,
        "interest_rate": r,
        "interest_method": deposit.interest_method,
        "daily_interest": daily_gross_avg,
        "monthly_interest": monthly_approx,
        "projected_maturity_amount": projected_maturity,
        "accrued_interest": accrued_interest,
        "completion_percent": completion_i,
        "elapsed_duration_display": f"{elapsed} day{'s' if elapsed != 1 else ''} in",
        "remaining_duration_display": f"{remaining} day{'s' if remaining != 1 else ''} left",
        "start_date": deposit.start_date,
        "maturity_date": deposit.maturity_date,
        "tenure_display": f"{total_days} day{'s' if total_days != 1 else ''}",
        "compounding_frequency": deposit.compounding_frequency or "",
        "payout_structure_display": deposit.payout_structure_display or "At maturity",
        "transaction_date": deposit.transaction_date,
        "interest_at_maturity_after_tax": net_full,
        "gross_interest": gross_full,
        "tax_rate": tax_rate,
        "tax_amount": tax_on_full,
        "net_interest": net_full,
        "auto_renewal": deposit.auto_renewal,
        "minimum_lock_period_display": (
            f"{deposit.minimum_lock_period_days} day{'s' if deposit.minimum_lock_period_days != 1 else ''}"
            if deposit.minimum_lock_period_days
            else "—"
        ),
        "early_withdrawal_penalty": deposit.early_withdrawal_penalty,
        "redeemable_monthly_interest": bool(deposit.redeemable_monthly_interest),
        "interest_ledger": interest_ledger,
    }


def portfolio_summary_for_user(user, as_of: date | None = None) -> dict[str, Decimal]:
    """
    Aggregate principal, accrued (net), projected maturity, and redeemable interest.
    Only Active + Matured deposits (excludes withdrawn/cancelled).
    """
    as_of = as_of or timezone.localdate()
    qs = GWCFixedDeposit.objects.filter(
        user=user,
        status__in=[
            GWCFixedDeposit.Status.ACTIVE,
            GWCFixedDeposit.Status.MATURED,
        ],
    )
    total_principal = Decimal("0")
    total_accrued = Decimal("0")
    total_maturity = Decimal("0")
    total_redeemable = Decimal("0")
    total_interest_redeemed = Decimal("0")
    for d in qs:
        row = deposit_to_display(d, as_of)
        total_principal += row["principal_amount"]
        total_accrued += row["accrued_interest"]
        total_maturity += row["projected_maturity_amount"]
        ledger = row["interest_ledger"]
        if ledger.get("enabled"):
            total_redeemable += ledger["redeemable"]
            total_interest_redeemed += ledger["total_redeemed"]
    return {
        "total_principal": total_principal.quantize(Q2, ROUND_HALF_UP),
        "total_accrued_interest": total_accrued.quantize(Q2, ROUND_HALF_UP),
        "total_maturity_value": total_maturity.quantize(Q2, ROUND_HALF_UP),
        "total_redeemable_interest": total_redeemable.quantize(Q2, ROUND_HALF_UP),
        "total_interest_redeemed": total_interest_redeemed.quantize(Q2, ROUND_HALF_UP),
    }


def redeemable_interest_summary_for_user(user, as_of: date | None = None) -> dict[str, Any]:
    """
    Deposits with redeemable_monthly_interest that currently have a redeemable balance.
    Used for home Matured projects card.
    """
    as_of = as_of or timezone.localdate()
    qs = GWCFixedDeposit.objects.filter(
        user=user,
        redeemable_monthly_interest=True,
        status__in=[
            GWCFixedDeposit.Status.ACTIVE,
            GWCFixedDeposit.Status.MATURED,
        ],
    ).order_by("start_date", "pk")
    deposits_out: list[dict[str, Any]] = []
    total_redeemable = ZERO
    total_earned = ZERO
    total_redeemed = ZERO
    total_principal = ZERO
    for deposit in qs:
        ledger = monthly_interest_ledger(deposit, as_of=as_of)
        if ledger["redeemable"] <= ZERO:
            continue
        total_redeemable += ledger["redeemable"]
        total_earned += ledger["total_earned"]
        total_redeemed += ledger["total_redeemed"]
        total_principal += deposit.principal_amount or ZERO
        deposits_out.append(
            {
                "deposit_id": deposit.deposit_id,
                "principal": deposit.principal_amount,
                "redeemable": ledger["redeemable"],
                "earned": ledger["total_earned"],
                "redeemed": ledger["total_redeemed"],
            }
        )
    primary = max(deposits_out, key=lambda d: d["redeemable"]) if deposits_out else None
    return {
        "has_redeemable": bool(deposits_out),
        "deposits": deposits_out,
        "deposit_count": len(deposits_out),
        "primary_deposit_id": primary["deposit_id"] if primary else None,
        "total_redeemable": total_redeemable.quantize(Q2, ROUND_HALF_UP),
        "total_earned": total_earned.quantize(Q2, ROUND_HALF_UP),
        "total_redeemed": total_redeemed.quantize(Q2, ROUND_HALF_UP),
        "total_principal": total_principal.quantize(Q2, ROUND_HALF_UP),
    }


def nearest_active_progress(user, as_of: date | None = None) -> dict[str, Any]:
    """Home-card progress from the nearest-maturing active deposit."""
    as_of = as_of or timezone.localdate()
    deposit = (
        GWCFixedDeposit.objects.filter(user=user, status=GWCFixedDeposit.Status.ACTIVE)
        .order_by("maturity_date", "pk")
        .first()
    )
    if not deposit:
        matured = GWCFixedDeposit.objects.filter(
            user=user, status=GWCFixedDeposit.Status.MATURED
        ).exists()
        return {
            "pct": 100 if matured else 0,
            "next_maturity": None,
            "has_active": False,
            "has_matured": matured,
        }
    row = deposit_to_display(deposit, as_of)
    return {
        "pct": int(row["completion_percent"] or 0),
        "next_maturity": deposit.maturity_date,
        "has_active": True,
        "has_matured": False,
    }


def recent_activities_for_user(user, limit: int = 25) -> list[dict[str, Any]]:
    qs = (
        GWCDepositActivity.objects.filter(deposit__user=user)
        .select_related("deposit")
        .order_by("-timestamp")[:limit]
    )
    out: list[dict[str, Any]] = []
    for a in qs:
        ts = timezone.localtime(a.timestamp)
        out.append(
            {
                "description": a.description,
                "timestamp": ts.strftime("%d %b %Y · %H:%M"),
                "deposit_id": a.deposit.deposit_id,
                "type": a.activity_type,
                "amount": a.amount,
            }
        )
    return out
