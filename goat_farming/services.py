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
ZERO = Decimal("0.00")


def unsettled_matured_purchases(profile, *, farm_id=None):
    """Allocated package cycles past the 14-month mark that are not yet settled."""
    cutoff = timezone.now() - timedelta(days=CGF_CYCLE_DAYS)
    qs = PackagePurchase.objects.filter(
        user=profile,
        status="allocated",
        settled_at__isnull=True,
        purchase_date__lte=cutoff,
    ).select_related("package", "farm")
    if farm_id is not None:
        qs = qs.filter(farm_id=farm_id)
    return list(qs.order_by("purchase_date", "pk"))


def matured_transfer_preview(profile, *, farm_id=None) -> dict:
    """Amounts available to transfer from matured (unsettled) CGF cycles."""
    matured = unsettled_matured_purchases(profile, farm_id=farm_id)
    matured_goats = sum(int(p.goats_allocated or 0) for p in matured)
    matured_kids = sum(
        int(p.goats_allocated or 0) * int(getattr(p.package, "kids_per_goat", 2) or 2)
        for p in matured
    )
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


def farm_maturity_flags(profile) -> dict[int, dict]:
    """Per-farm maturity / transfer flags for dashboard rows."""
    now = timezone.now()
    cutoff = now - timedelta(days=CGF_CYCLE_DAYS)
    flags: dict[int, dict] = {}

    accounts = UserFarmAccount.objects.filter(user=profile, is_active=True).select_related(
        "farm"
    )
    for account in accounts:
        created = account.created_at
        is_cycle_complete = bool(created and created <= cutoff)
        flags[account.farm_id] = {
            "farm_id": account.farm_id,
            "is_cycle_complete": is_cycle_complete,
            "can_transfer": False,
            "transfer_amount": ZERO,
            "matured_goats": 0,
            "matured_kids": 0,
            "matured_count": 0,
        }

    for purchase in unsettled_matured_purchases(profile):
        farm_id = purchase.farm_id
        if farm_id not in flags:
            flags[farm_id] = {
                "farm_id": farm_id,
                "is_cycle_complete": True,
                "can_transfer": False,
                "transfer_amount": ZERO,
                "matured_goats": 0,
                "matured_kids": 0,
                "matured_count": 0,
            }
        goats = int(purchase.goats_allocated or 0)
        kids = goats * int(getattr(purchase.package, "kids_per_goat", 2) or 2)
        flags[farm_id]["is_cycle_complete"] = True
        flags[farm_id]["matured_goats"] += goats
        flags[farm_id]["matured_kids"] += kids
        flags[farm_id]["matured_count"] += 1
        flags[farm_id]["transfer_amount"] += Decimal(goats + kids) * CGF_CASHOUT_PRICE_PER_GOAT
        flags[farm_id]["can_transfer"] = flags[farm_id]["transfer_amount"] > ZERO

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
    - Goat holdings reduced by matured goats_allocated
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
        goats_by_farm[purchase.farm_id] = goats_by_farm.get(purchase.farm_id, 0) + int(
            purchase.goats_allocated or 0
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
