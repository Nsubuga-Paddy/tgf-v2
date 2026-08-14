"""Personal 52-week cycle lifecycle for 52WSC."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Sum, Case, When, F, Value, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone

from savings_52_weeks.interest_utils import calculate_unfixed_interest_for_period
from savings_52_weeks.models import SavingsCycle, SavingsTransaction

CYCLE_WEEKS = 52
CYCLE_DAYS = CYCLE_WEEKS * 7
WEEK_UNIT = Decimal("10000")
TARGET_AMOUNT = Decimal("13780000")
ZERO = Decimal("0.00")
# First wave of personal cycles starts with 2026 deposits (2025 kept as history).
PERSONAL_CYCLE_EPOCH = date(2026, 1, 1)


def cycle_end_date(start: date) -> date:
    return start + timedelta(days=CYCLE_DAYS)


def personal_week_number(start: date, today: date | None = None) -> int:
    today = today or timezone.localdate()
    if today < start:
        return 1
    week = (today - start).days // 7 + 1
    return min(max(week, 1), CYCLE_WEEKS)


def required_savings_for_week(week: int) -> Decimal:
    week = min(max(int(week), 1), CYCLE_WEEKS)
    return Decimal(week) * WEEK_UNIT


def _q(value) -> Decimal:
    return (value or ZERO).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _net_amount_aggregate(qs) -> Decimal:
    result = qs.aggregate(
        total=Coalesce(
            Sum(
                Case(
                    When(transaction_type="deposit", then=F("amount")),
                    When(transaction_type="withdrawal", then=-F("amount")),
                    When(transaction_type="gwc_contribution", then=-F("amount")),
                    default=Value(ZERO),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            ),
            Value(ZERO, output_field=DecimalField(max_digits=14, decimal_places=2)),
        )
    )["total"]
    return _q(result)


def latest_balance_forward(cycle: SavingsCycle) -> Decimal:
    latest = (
        cycle.transactions.filter(transaction_type="deposit")
        .order_by("-created_at")
        .first()
    )
    if latest and latest.remaining_balance is not None:
        return _q(latest.remaining_balance)
    return _q(cycle.opening_balance)


def weeks_completed_for_cycle(cycle: SavingsCycle) -> int:
    covered = set()
    for tx in cycle.transactions.filter(transaction_type="deposit"):
        for week_data in tx.fully_covered_weeks or []:
            if week_data.get("fully_covered"):
                covered.add(int(week_data["week"]))
    return len(covered)


def next_week_for_cycle(cycle: SavingsCycle) -> int:
    latest = (
        cycle.transactions.filter(transaction_type="deposit")
        .order_by("-created_at")
        .first()
    )
    if latest and latest.next_week:
        return int(latest.next_week)
    return 1


def _next_cycle_number(profile) -> int:
    latest = (
        SavingsCycle.objects.filter(user_profile=profile)
        .order_by("-cycle_number")
        .values_list("cycle_number", flat=True)
        .first()
    )
    return int(latest or 0) + 1


def _create_cycle(profile, *, start: date, opening_balance: Decimal, cycle_number: int):
    return SavingsCycle.objects.create(
        user_profile=profile,
        cycle_number=cycle_number,
        start_date=start,
        end_date=cycle_end_date(start),
        status=SavingsCycle.STATUS_ACTIVE,
        opening_balance=_q(opening_balance),
    )


def attach_deposit_to_cycle(deposit: SavingsTransaction) -> SavingsCycle | None:
    """Assign a deposit to the member's active personal cycle."""
    if deposit.transaction_type != "deposit":
        return deposit.cycle
    profile = deposit.user_profile
    tx_date = deposit.transaction_date or timezone.localdate()
    if tx_date < PERSONAL_CYCLE_EPOCH and not deposit.cycle_id:
        return None

    cycle = (
        SavingsCycle.objects.filter(
            user_profile=profile,
            status__in=[
                SavingsCycle.STATUS_ACTIVE,
                SavingsCycle.STATUS_AWAITING_DECISION,
                SavingsCycle.STATUS_POT_AVAILABLE,
            ],
        )
        .order_by("-cycle_number")
        .first()
    )

    if cycle and cycle.status == SavingsCycle.STATUS_ACTIVE:
        deposit.cycle = cycle
        return cycle

    if cycle and cycle.status in (
        SavingsCycle.STATUS_AWAITING_DECISION,
        SavingsCycle.STATUS_POT_AVAILABLE,
    ):
        active = active_cycle_for_progress(profile)
        if active:
            deposit.cycle = active
            return active
        # Wait for member decision before opening the next cycle automatically.
        return deposit.cycle

    new_cycle = _create_cycle(
        profile,
        start=tx_date,
        opening_balance=ZERO,
        cycle_number=_next_cycle_number(profile),
    )
    deposit.cycle = new_cycle
    return new_cycle


def backfill_cycles_for_profile(profile) -> SavingsCycle | None:
    """Ensure a personal cycle exists from the first 2026 deposit onward."""
    first = (
        profile.savings_transactions.filter(
            transaction_type="deposit",
            transaction_date__gte=PERSONAL_CYCLE_EPOCH,
        )
        .order_by("transaction_date", "created_at", "pk")
        .first()
    )
    if not first:
        return None

    cycle = (
        SavingsCycle.objects.filter(user_profile=profile)
        .order_by("cycle_number")
        .first()
    )
    if not cycle:
        cycle = _create_cycle(
            profile,
            start=first.transaction_date,
            opening_balance=ZERO,
            cycle_number=1,
        )
    elif (
        cycle.status == SavingsCycle.STATUS_ACTIVE
        and cycle.start_date != first.transaction_date
        and cycle.cycle_number == 1
    ):
        cycle.start_date = first.transaction_date
        cycle.end_date = cycle_end_date(first.transaction_date)
        cycle.save(update_fields=["start_date", "end_date", "updated_at"])

    open_statuses = {
        SavingsCycle.STATUS_ACTIVE,
        SavingsCycle.STATUS_AWAITING_DECISION,
        SavingsCycle.STATUS_POT_AVAILABLE,
    }
    target = (
        SavingsCycle.objects.filter(user_profile=profile, status__in=open_statuses)
        .order_by("cycle_number")
        .first()
    ) or cycle

    deposits = profile.savings_transactions.filter(
        transaction_type="deposit",
        transaction_date__gte=target.start_date,
        cycle__isnull=True,
    ).order_by("transaction_date", "created_at", "pk")

    for dep in deposits:
        dep.cycle = target
        dep.calculate_covered_weeks()
        SavingsTransaction.objects.filter(pk=dep.pk).update(
            cycle=target,
            fully_covered_weeks=dep.fully_covered_weeks,
            remaining_balance=dep.remaining_balance,
            cumulative_total=dep.cumulative_total,
            next_week=dep.next_week,
        )

    return target


def _snapshot_maturity_amounts(cycle: SavingsCycle) -> dict:
    tx_qs = cycle.transactions.all()
    net = _net_amount_aggregate(tx_qs) + _q(cycle.opening_balance)
    bf = latest_balance_forward(cycle)
    amount_saved = max(net - bf, ZERO)
    interest = calculate_unfixed_interest_for_period(
        cycle.user_profile,
        cycle.start_date,
        min(timezone.localdate(), cycle.end_date),
    )
    return {
        "amount_saved": _q(amount_saved),
        "interest_earned": _q(interest),
        "balance_brought_forward": _q(bf),
    }


@transaction.atomic
def maybe_mature_cycle(cycle: SavingsCycle) -> SavingsCycle:
    if cycle.status != SavingsCycle.STATUS_ACTIVE:
        return cycle
    today = timezone.localdate()
    if today < cycle.end_date:
        return cycle

    snap = _snapshot_maturity_amounts(cycle)
    cycle.amount_saved = snap["amount_saved"]
    cycle.interest_earned = snap["interest_earned"]
    cycle.balance_brought_forward = snap["balance_brought_forward"]
    cycle.status = SavingsCycle.STATUS_AWAITING_DECISION
    cycle.matured_at = timezone.now()
    cycle.save(
        update_fields=[
            "amount_saved",
            "interest_earned",
            "balance_brought_forward",
            "status",
            "matured_at",
            "updated_at",
        ]
    )
    return cycle


def date_label(value) -> str:
    if not value:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%d %b %Y")
    return str(value)


def money_int(value) -> int:
    return int(_q(value))


def cycle_deposit_total(cycle: SavingsCycle) -> Decimal:
    total = cycle.transactions.filter(transaction_type="deposit").aggregate(
        total=Coalesce(Sum("amount"), Value(ZERO))
    )["total"]
    return _q(total) + _q(cycle.opening_balance)


def active_cycle_for_progress(profile) -> SavingsCycle | None:
    return (
        SavingsCycle.objects.filter(
            user_profile=profile, status=SavingsCycle.STATUS_ACTIVE
        )
        .order_by("-cycle_number")
        .first()
    )


def build_cycle_payload(profile, cycle: SavingsCycle | None) -> dict:
    today = timezone.localdate()
    decision = (
        SavingsCycle.objects.filter(
            user_profile=profile, status=SavingsCycle.STATUS_AWAITING_DECISION
        )
        .order_by("-cycle_number")
        .first()
    )
    pot = (
        SavingsCycle.objects.filter(
            user_profile=profile, status=SavingsCycle.STATUS_POT_AVAILABLE
        )
        .order_by("-cycle_number")
        .first()
    )
    active = active_cycle_for_progress(profile)
    display = active or decision or pot or cycle

    if not display:
        return {
            "cycle": None,
            "personalWeek": 1,
            "requiredSavings": money_int(WEEK_UNIT),
            "remainingWeeks": CYCLE_WEEKS - 1,
            "cycleStartDate": None,
            "cycleEndDate": None,
            "cycleComplete": False,
            "weeksCompleted": 0,
            "nextWeekToCover": 1,
            "balanceBroughtForward": 0,
            "maturedCycle": None,
            "cycleLabel": None,
            "cycleDeposits": 0,
            "progressPercentage": 0.0,
        }

    if active:
        week = personal_week_number(active.start_date, today)
        bf = latest_balance_forward(active)
        weeks_done = weeks_completed_for_cycle(active)
        next_week = next_week_for_cycle(active)
        progress_cycle = active
    elif decision:
        week = CYCLE_WEEKS
        bf = _q(decision.balance_brought_forward)
        weeks_done = max(weeks_completed_for_cycle(decision), CYCLE_WEEKS)
        next_week = 53
        progress_cycle = decision
    else:
        week = personal_week_number(display.start_date, today)
        bf = latest_balance_forward(display) if display.status == SavingsCycle.STATUS_ACTIVE else _q(display.balance_brought_forward)
        weeks_done = weeks_completed_for_cycle(display)
        next_week = next_week_for_cycle(display)
        progress_cycle = display

    show = decision or pot
    matured = None
    if show:
        status_key = (
            "awaiting_decision"
            if show.status == SavingsCycle.STATUS_AWAITING_DECISION
            else "new_cycle_started"
            if show.status == SavingsCycle.STATUS_POT_AVAILABLE
            else show.status
        )
        matured = {
            "id": show.pk,
            "label": show.label,
            "startDate": date_label(show.start_date),
            "maturedOn": date_label(
                show.matured_at.date() if show.matured_at else show.end_date
            ),
            "weeksCompleted": CYCLE_WEEKS,
            "amountSaved": money_int(show.amount_saved),
            "interestEarned": money_int(show.interest_earned),
            "balanceBroughtForward": money_int(show.balance_brought_forward),
            "status": status_key,
        }

    deposits = cycle_deposit_total(progress_cycle)
    return {
        "cycle": progress_cycle,
        "personalWeek": week,
        "requiredSavings": money_int(required_savings_for_week(week)),
        "remainingWeeks": max(CYCLE_WEEKS - week, 0),
        "cycleStartDate": date_label(progress_cycle.start_date),
        "cycleEndDate": date_label(progress_cycle.end_date),
        "cycleComplete": bool(decision or (progress_cycle.status != SavingsCycle.STATUS_ACTIVE and not active)),
        "weeksCompleted": weeks_done,
        "nextWeekToCover": next_week,
        "balanceBroughtForward": money_int(bf),
        "maturedCycle": matured,
        "cycleLabel": progress_cycle.label,
        "cycleDeposits": money_int(deposits),
        "progressPercentage": float(min((deposits / TARGET_AMOUNT) * 100, 100)),
    }


def sync_member_cycles(profile) -> dict:
    """Backfill + mature as needed. Returns cycle summary for API."""
    cycle = backfill_cycles_for_profile(profile)
    if cycle and cycle.status == SavingsCycle.STATUS_ACTIVE:
        cycle = maybe_mature_cycle(cycle)
    else:
        active = active_cycle_for_progress(profile)
        if active:
            maybe_mature_cycle(active)
    return build_cycle_payload(profile, cycle)


@transaction.atomic
def start_new_cycle_with_bf(profile, *, actor=None) -> SavingsCycle:
    cycle = (
        SavingsCycle.objects.select_for_update()
        .filter(user_profile=profile, status=SavingsCycle.STATUS_AWAITING_DECISION)
        .order_by("-cycle_number")
        .first()
    )
    if not cycle:
        raise ValueError("You do not have a matured cycle waiting for a decision.")

    bf = _q(cycle.balance_brought_forward)
    today = timezone.localdate()
    new_cycle = _create_cycle(
        profile,
        start=today,
        opening_balance=bf,
        cycle_number=_next_cycle_number(profile),
    )
    cycle.status = SavingsCycle.STATUS_POT_AVAILABLE
    cycle.settlement_action = "start_new_cycle"
    cycle.seeded_next_cycle = new_cycle
    cycle.balance_brought_forward = ZERO
    cycle.notes = (
        f"{(cycle.notes or '').strip()}\nStarted Cycle {new_cycle.cycle_number} with BF {bf}."
    ).strip()
    cycle.save(
        update_fields=[
            "status",
            "settlement_action",
            "seeded_next_cycle",
            "balance_brought_forward",
            "notes",
            "updated_at",
        ]
    )
    return new_cycle


@transaction.atomic
def transfer_all_to_main(profile, *, actor=None) -> SavingsCycle:
    from main_account import services as main_account_ledger

    cycle = (
        SavingsCycle.objects.select_for_update()
        .filter(user_profile=profile, status=SavingsCycle.STATUS_AWAITING_DECISION)
        .order_by("-cycle_number")
        .first()
    )
    if not cycle:
        raise ValueError("You do not have a matured cycle waiting for a decision.")

    principal = _q(cycle.amount_saved) + _q(cycle.balance_brought_forward)
    interest = _q(cycle.interest_earned)
    total = principal + interest
    if total <= ZERO:
        raise ValueError("There is nothing available to transfer for this cycle.")

    main_tx = main_account_ledger.transfer_from_project(
        profile,
        "52 Weeks Saving Challenge",
        total,
        description=(
            f"Matured 52WSC {cycle.label}: saved {_q(cycle.amount_saved)} + "
            f"interest {interest} + BF {_q(cycle.balance_brought_forward)}"
        ),
        created_by=actor,
    )
    if principal > ZERO:
        SavingsTransaction.objects.create(
            user_profile=profile,
            amount=principal,
            transaction_type="withdrawal",
            transaction_date=timezone.localdate(),
            receipt_number=f"52WSC-TRF-{cycle.pk}",
            cycle=cycle,
        )

    cycle.status = SavingsCycle.STATUS_SETTLED
    cycle.settled_at = timezone.now()
    cycle.settlement_action = "transfer_all"
    cycle.main_account_transaction = main_tx
    cycle.balance_brought_forward = ZERO
    cycle.amount_saved = ZERO
    cycle.save(
        update_fields=[
            "status",
            "settled_at",
            "settlement_action",
            "main_account_transaction",
            "balance_brought_forward",
            "amount_saved",
            "updated_at",
        ]
    )
    return cycle


@transaction.atomic
def transfer_matured_pot_to_main(profile, *, actor=None) -> SavingsCycle:
    from main_account import services as main_account_ledger

    cycle = (
        SavingsCycle.objects.select_for_update()
        .filter(user_profile=profile, status=SavingsCycle.STATUS_POT_AVAILABLE)
        .order_by("-cycle_number")
        .first()
    )
    if not cycle:
        raise ValueError("You do not have a matured pot available to transfer.")

    principal = _q(cycle.amount_saved)
    interest = _q(cycle.interest_earned)
    total = principal + interest
    if total <= ZERO:
        raise ValueError("Matured pot is empty.")

    main_tx = main_account_ledger.transfer_from_project(
        profile,
        "52 Weeks Saving Challenge",
        total,
        description=(
            f"Matured 52WSC pot {cycle.label}: saved {principal} + interest {interest}"
        ),
        created_by=actor,
    )
    if principal > ZERO:
        SavingsTransaction.objects.create(
            user_profile=profile,
            amount=principal,
            transaction_type="withdrawal",
            transaction_date=timezone.localdate(),
            receipt_number=f"52WSC-POT-{cycle.pk}",
            cycle=cycle,
        )

    cycle.status = SavingsCycle.STATUS_SETTLED
    cycle.settled_at = timezone.now()
    cycle.settlement_action = "transfer_pot"
    cycle.main_account_transaction = main_tx
    cycle.amount_saved = ZERO
    cycle.interest_earned = ZERO
    cycle.save(
        update_fields=[
            "status",
            "settled_at",
            "settlement_action",
            "main_account_transaction",
            "amount_saved",
            "interest_earned",
            "updated_at",
        ]
    )
    return cycle
