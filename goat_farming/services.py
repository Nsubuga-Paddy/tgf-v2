"""Business operations for Commercial Goat Farming."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from goat_farming.models import (
    CGF_CASHOUT_PRICE_PER_GOAT,
    CGFActionRequest,
    PackagePurchase,
    UserFarmAccount,
)

CGF_CYCLE_DAYS = 425
# Fully paid or goats allocated — payment ledger rows are not required.
CGF_ELIGIBLE_STATUSES = ("paid", "allocated")
ZERO = Decimal("0.00")


def purchase_cycle_goats(purchase) -> int:
    """Goats counted for a cycle: allocated count, else package size when fully paid."""
    allocated = int(purchase.goats_allocated or 0)
    if allocated > 0:
        return allocated
    package = getattr(purchase, "package", None)
    if package is not None:
        return int(package.goat_count or 0)
    return 0


def purchase_cycle_kids(purchase) -> int:
    goats = purchase_cycle_goats(purchase)
    package = getattr(purchase, "package", None)
    kids_per = int(getattr(package, "kids_per_goat", 2) or 2) if package else 2
    return goats * kids_per


def maturity_datetime(purchase_date):
    """Cycle end = purchase_date + 425 days (~14 months)."""
    if not purchase_date:
        return None
    return purchase_date + timedelta(days=CGF_CYCLE_DAYS)


def is_purchase_matured(purchase, *, now=None) -> bool:
    now = now or timezone.now()
    matures = maturity_datetime(purchase.purchase_date)
    return bool(matures and matures <= now)


def cycle_progress_pct(purchase_date, *, now=None) -> int:
    """Elapsed days since purchase / 425, capped at 100."""
    if not purchase_date:
        return 0
    now = now or timezone.now()
    elapsed = (now - purchase_date).total_seconds() / 86400.0
    if elapsed <= 0:
        return 0
    pct = int(round((elapsed / CGF_CYCLE_DAYS) * 100))
    return max(0, min(100, pct))


def days_until_maturity(purchase_date, *, now=None) -> int | None:
    matures = maturity_datetime(purchase_date)
    if not matures:
        return None
    now = now or timezone.now()
    delta = (matures - now).total_seconds() / 86400.0
    return int(round(delta))


def eligible_cycle_queryset(profile=None, *, farm_id=None, unsettled_only=True):
    """Package purchases that participate in the 14-month maturity cycle."""
    qs = PackagePurchase.objects.filter(status__in=CGF_ELIGIBLE_STATUSES).select_related(
        "package", "farm", "user"
    )
    if profile is not None:
        qs = qs.filter(user=profile)
    if unsettled_only:
        qs = qs.filter(settled_at__isnull=True)
    if farm_id is not None:
        qs = qs.filter(farm_id=farm_id)
    return qs.order_by("purchase_date", "pk")


def unsettled_matured_purchases(profile, *, farm_id=None):
    """Fully paid / allocated cycles past the 14-month mark that are not yet settled."""
    cutoff = timezone.now() - timedelta(days=CGF_CYCLE_DAYS)
    qs = eligible_cycle_queryset(profile, farm_id=farm_id, unsettled_only=True).filter(
        purchase_date__lte=cutoff,
        purchase_date__isnull=False,
    )
    return list(qs)


def matured_transfer_preview(profile, *, farm_id=None) -> dict:
    """Amounts available to transfer from matured (unsettled) CGF cycles."""
    matured = unsettled_matured_purchases(profile, farm_id=farm_id)
    matured_goats = sum(purchase_cycle_goats(p) for p in matured)
    matured_kids = sum(purchase_cycle_kids(p) for p in matured)
    principal = sum((p.amount_paid or p.total_amount or ZERO) for p in matured)
    if not isinstance(principal, Decimal):
        principal = Decimal(str(principal or 0))
    units = matured_goats + matured_kids
    available = Decimal(units) * CGF_CASHOUT_PRICE_PER_GOAT
    return {
        "purchases": matured,
        "matured_count": len(matured),
        "matured_goats": matured_goats,
        "matured_kids": matured_kids,
        "principal": principal,
        "available": available,
        "can_transfer": bool(matured) and available > ZERO,
        "farm_id": farm_id,
    }


def member_cycle_progress(profile) -> dict:
    """
    Home-card progress for CGF: based on the next unsettled cycle to mature
    (oldest active). If all eligible cycles are matured, progress is 100%.
    """
    now = timezone.now()
    eligible = list(eligible_cycle_queryset(profile, unsettled_only=True))
    if not eligible:
        return {
            "pct": 0,
            "next_maturity_at": None,
            "matured_count": 0,
            "active_count": 0,
        }

    matured = [p for p in eligible if is_purchase_matured(p, now=now)]
    active = [p for p in eligible if not is_purchase_matured(p, now=now)]

    if not active:
        dates = [p.purchase_date for p in matured if p.purchase_date]
        earliest = min(dates) if dates else None
        return {
            "pct": 100,
            "next_maturity_at": maturity_datetime(earliest) if earliest else None,
            "matured_count": len(matured),
            "active_count": 0,
        }

    next_purchase = min(active, key=lambda p: (p.purchase_date, p.pk))
    return {
        "pct": cycle_progress_pct(next_purchase.purchase_date, now=now),
        "next_maturity_at": maturity_datetime(next_purchase.purchase_date),
        "matured_count": len(matured),
        "active_count": len(active),
    }


def farm_maturity_flags(profile) -> dict[int, dict]:
    """Per-farm maturity / transfer flags driven by package purchase_date + 425 days."""
    now = timezone.now()
    flags: dict[int, dict] = {}

    accounts = UserFarmAccount.objects.filter(user=profile, is_active=True).select_related(
        "farm"
    )
    for account in accounts:
        flags[account.farm_id] = {
            "farm_id": account.farm_id,
            "is_cycle_complete": False,
            "can_transfer": False,
            "transfer_amount": ZERO,
            "matured_goats": 0,
            "matured_kids": 0,
            "matured_count": 0,
            "next_maturity_at": None,
            "progress_pct": 0,
            "cycle_start_at": None,
        }

    eligible = list(eligible_cycle_queryset(profile, unsettled_only=True))
    by_farm: dict[int, list] = {}
    for purchase in eligible:
        by_farm.setdefault(purchase.farm_id, []).append(purchase)

    for farm_id, purchases in by_farm.items():
        if farm_id not in flags:
            flags[farm_id] = {
                "farm_id": farm_id,
                "is_cycle_complete": False,
                "can_transfer": False,
                "transfer_amount": ZERO,
                "matured_goats": 0,
                "matured_kids": 0,
                "matured_count": 0,
                "next_maturity_at": None,
                "progress_pct": 0,
                "cycle_start_at": None,
            }

        matured = [p for p in purchases if is_purchase_matured(p, now=now)]
        active = [p for p in purchases if not is_purchase_matured(p, now=now)]

        for purchase in matured:
            goats = purchase_cycle_goats(purchase)
            kids = purchase_cycle_kids(purchase)
            flags[farm_id]["matured_goats"] += goats
            flags[farm_id]["matured_kids"] += kids
            flags[farm_id]["matured_count"] += 1
            flags[farm_id]["transfer_amount"] += Decimal(goats + kids) * CGF_CASHOUT_PRICE_PER_GOAT

        flags[farm_id]["is_cycle_complete"] = bool(matured)
        flags[farm_id]["can_transfer"] = flags[farm_id]["transfer_amount"] > ZERO

        if active:
            next_p = min(active, key=lambda p: (p.purchase_date, p.pk))
            flags[farm_id]["cycle_start_at"] = next_p.purchase_date
            flags[farm_id]["next_maturity_at"] = maturity_datetime(next_p.purchase_date)
            flags[farm_id]["progress_pct"] = cycle_progress_pct(
                next_p.purchase_date, now=now
            )
        elif matured:
            oldest = min(matured, key=lambda p: (p.purchase_date, p.pk))
            flags[farm_id]["cycle_start_at"] = oldest.purchase_date
            flags[farm_id]["next_maturity_at"] = maturity_datetime(oldest.purchase_date)
            flags[farm_id]["progress_pct"] = 100

    return flags


@transaction.atomic
def transfer_matured_cgf_to_main(
    profile, *, actor=None, notes: str = "", farm_id=None
) -> CGFActionRequest:
    """
    Credit Main Account with the cash value of unsettled matured CGF cycles.

    Optionally scoped to one farm. Audit trail:
    - CGFActionRequest (transfer_to_main, processed)
    - PackagePurchase.settled_at linked to that action
    - MainAccountTransaction (project_transfer_in)
    - Goat holdings reduced by matured goats on farm (allocated count)
    """
    from main_account import services as main_account_ledger

    preview = matured_transfer_preview(profile, farm_id=farm_id)
    purchases = preview["purchases"]
    available = preview["available"]
    if not preview["can_transfer"]:
        raise ValueError("You do not have matured CGF cycles ready to transfer.")

    goats_count = preview["matured_goats"] + preview["matured_kids"]
    farm = purchases[0].farm if len({p.farm_id for p in purchases}) == 1 else None
    now = timezone.now()
    scope = f"farm {farm.name}" if farm else "all farms"
    note = (notes or "").strip() or (
        f"Transferred matured CGF value to Main Account ({scope}: "
        f"{preview['matured_count']} cycle(s), "
        f"{preview['matured_goats']} goats + {preview['matured_kids']} kids)."
    )

    action = CGFActionRequest.objects.create(
        user_profile=profile,
        farm=farm,
        request_type="transfer_to_main",
        goats_count=goats_count,
        amount=available,
        notes=note,
        status="processed",
        admin_notes="Member-initiated transfer of matured CGF cycles to Main Account.",
        processed_at=now,
    )

    main_tx = main_account_ledger.transfer_from_project(
        profile,
        "Commercial Goat Farming",
        available,
        description=(
            f"Matured CGF transfer #{action.pk}: "
            f"{preview['matured_goats']} goats + {preview['matured_kids']} kids"
            + (f" · {farm.name}" if farm else "")
        ),
        created_by=actor,
    )
    action.main_account_transaction = main_tx
    action.save(update_fields=["main_account_transaction"])

    goats_by_farm: dict[int, int] = {}
    for purchase in purchases:
        # Only reduce ledger goats that were actually allocated onto the farm.
        allocated = int(purchase.goats_allocated or 0)
        if allocated > 0:
            goats_by_farm[purchase.farm_id] = (
                goats_by_farm.get(purchase.farm_id, 0) + allocated
            )
        purchase.settled_at = now
        purchase.settlement_action = action
        purchase.save(update_fields=["settled_at", "settlement_action"])

    for farm_pk, goats_to_remove in goats_by_farm.items():
        account = (
            UserFarmAccount.objects.select_for_update()
            .filter(user=profile, farm_id=farm_pk)
            .first()
        )
        if not account or goats_to_remove <= 0:
            continue
        account.current_goats = max(0, int(account.current_goats or 0) - goats_to_remove)
        account.save(update_fields=["current_goats"])

    return action
