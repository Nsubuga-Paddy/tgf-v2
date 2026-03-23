"""
Interest math and dashboard DTOs for GWC fixed deposits.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from math import pow
from typing import Any

from django.utils import timezone

from .models import GWCDepositActivity, GWCFixedDeposit

Q2 = Decimal("0.01")


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

    return {
        "deposit_id": deposit.deposit_id,
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
        # Net of internal tax (same as projected maturity − principal); not labeled as tax on UI
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
    }


def portfolio_summary_for_user(user, as_of: date | None = None) -> dict[str, Decimal]:
    """
    Aggregate principal, accrued (net), and projected maturity value.
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
    for d in qs:
        row = deposit_to_display(d, as_of)
        total_principal += row["principal_amount"]
        total_accrued += row["accrued_interest"]
        total_maturity += row["projected_maturity_amount"]
    return {
        "total_principal": total_principal.quantize(Q2, ROUND_HALF_UP),
        "total_accrued_interest": total_accrued.quantize(Q2, ROUND_HALF_UP),
        "total_maturity_value": total_maturity.quantize(Q2, ROUND_HALF_UP),
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
