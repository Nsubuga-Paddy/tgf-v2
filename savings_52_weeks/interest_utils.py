"""
Utilities for calculating 15% annualized interest on unfixed savings.
Interest accrues daily but is deposited once at year-end (Dec 31).
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
from django.db.models import Sum, Case, When, F, Value, DecimalField
from django.db.models.functions import Coalesce


DAILY_RATE = Decimal("0.15") / Decimal("365")


def get_net_deposits_as_of(user_profile, as_of_date: date) -> Decimal:
    """
    Net deposits (deposits - withdrawals - GWC) from all transactions
    with transaction_date < as_of_date.
    """
    from savings_52_weeks.models import SavingsTransaction
    result = user_profile.savings_transactions.filter(
        transaction_date__lt=as_of_date
    ).aggregate(
        total=Coalesce(
            Sum(
                Case(
                    When(transaction_type='deposit', then=F('amount')),
                    When(transaction_type='withdrawal', then=-F('amount')),
                    When(transaction_type='gwc_contribution', then=-F('amount')),
                    default=Value(Decimal("0.00")),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            ),
            Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2)),
        )
    )['total'] or Decimal("0.00")
    return result


def get_total_invested_as_of(user_profile, as_of_date: date) -> Decimal:
    """
    Total amount in fixed deposits as of the given date.
    An investment is 'fixed' on date D if start_date <= D < maturity_date.
    Note: maturity_date is a property (not a DB field), so we filter in Python.
    """
    from savings_52_weeks.models import Investment, add_months

    investments = Investment.objects.filter(
        user_profile=user_profile,
        start_date__lte=as_of_date,
    )
    total = Decimal("0.00")
    for inv in investments:
        maturity = add_months(inv.start_date, inv.maturity_months)
        if maturity > as_of_date:  # Not yet matured as of this date
            total += inv.amount_invested or Decimal("0.00")
    return total


def get_unfixed_balance_as_of(user_profile, as_of_date: date) -> Decimal:
    """Unfixed balance = net deposits - total invested (as of start of day)."""
    net = get_net_deposits_as_of(user_profile, as_of_date)
    invested = get_total_invested_as_of(user_profile, as_of_date)
    return max(Decimal("0.00"), net - invested)


def calculate_unfixed_interest_for_period(
    user_profile,
    start_date: date,
    end_date: date,
) -> Decimal:
    """
    Calculate total interest on unfixed savings for each day in [start_date, end_date].
    Each day: interest += unfixed_balance_at_start_of_day * 0.15 / 365
    """
    total_interest = Decimal("0.00")
    current = start_date
    while current <= end_date:
        unfixed = get_unfixed_balance_as_of(user_profile, current)
        daily_interest = (unfixed * DAILY_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_interest += daily_interest
        current += timedelta(days=1)
    return total_interest.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_unfixed_interest_ytd(user_profile, year: int = None) -> Decimal:
    """
    Interest earned on unfixed savings from Jan 1 to today (year-to-date).
    For display in the Interest Earned card, updated daily.
    """
    from django.utils import timezone
    today = timezone.localdate()
    if year is None:
        year = today.year
    start = date(year, 1, 1)
    end = min(today, date(year, 12, 31))
    if start > end:
        return Decimal("0.00")
    return calculate_unfixed_interest_for_period(user_profile, start, end)


def calculate_unfixed_interest_for_year(user_profile, year: int) -> Decimal:
    """
    Total interest on unfixed savings for the full calendar year.
    Used for the year-end deposit on Dec 31.
    """
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    return calculate_unfixed_interest_for_period(user_profile, start, end)


def get_expected_full_year_interest(user_profile) -> Decimal:
    """
    Simple estimate: unfixed_now * 15%. For display in card.
    """
    from django.utils import timezone
    today = timezone.localdate()
    # Balance including today's transactions
    unfixed = get_unfixed_balance_as_of(user_profile, today + timedelta(days=1))
    return (unfixed * Decimal("0.15")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
