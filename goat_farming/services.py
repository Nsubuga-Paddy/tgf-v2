"""Business operations for Commercial Goat Farming."""

from __future__ import annotations

from calendar import monthrange
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from django.db import transaction
from django.utils import timezone

from accounts.models import MemberNotification
from main_account import services as main_ledger

from goat_farming.models import (
    CGF_CASHOUT_PRICE_PER_GOAT,
    CGFActionRequest,
    DEFAULT_CGF_CYCLE_MONTHS,
    Farm,
    InvestmentPackage,
    PackagePurchase,
    Payment,
    UserFarmAccount,
)

# Fully paid or goats allocated — payment ledger rows are not required.
CGF_ELIGIBLE_STATUSES = ("paid", "allocated")
ZERO = Decimal("0.00")
PROJECT_LABEL = "Commercial Goat Farming"
Q2 = Decimal("0.01")
DEFAULT_CASHOUT_PER_GOAT = CGF_CASHOUT_PRICE_PER_GOAT


def _q(amount) -> Decimal:
    return Decimal(amount or 0).quantize(Q2, ROUND_HALF_UP)


def purchasable_packages():
    """Only currently active packages can be bought from Main Account."""
    return InvestmentPackage.objects.filter(is_active=True).select_related(
        "management_fee_tier"
    ).order_by("goat_count", "name", "pk")


def default_purchase_farm(profile) -> Farm:
    """Prefer a farm the member already uses; otherwise the first active farm."""
    existing = (
        UserFarmAccount.objects.filter(user=profile, is_active=True)
        .select_related("farm")
        .order_by("farm__name", "pk")
        .first()
    )
    if existing and existing.farm_id:
        return existing.farm
    farm = Farm.objects.filter(is_active=True).order_by("name", "pk").first()
    if not farm:
        raise ValueError("No active goat farm is available for package purchases yet.")
    return farm


def serialize_package(package: InvestmentPackage) -> dict[str, Any]:
    goat_count = int(package.goat_count or 0)
    kids_per_goat = int(package.kids_per_goat or 2)
    expected_kids = goat_count * kids_per_goat
    harvest = goat_count + expected_kids
    cashout = Decimal(harvest) * DEFAULT_CASHOUT_PER_GOAT
    return {
        "id": package.pk,
        "name": package.name,
        "goatCount": goat_count,
        "kidsPerGoat": kids_per_goat,
        "expectedKids": expected_kids,
        "harvestGoats": harvest,
        "cycleDurationMonths": int(package.cycle_duration_months or DEFAULT_CGF_CYCLE_MONTHS),
        "goatUnitPrice": float(package.goat_unit_price or ZERO),
        "managementFee": float(package.management_fee or ZERO),
        "totalCost": float(package.total_cost or ZERO),
        "cashoutPerGoat": float(DEFAULT_CASHOUT_PER_GOAT),
        "expectedCashout": float(cashout),
    }


def build_purchase_options(profile) -> dict[str, Any]:
    available = main_ledger.available_balance(profile)
    packages = [serialize_package(pkg) for pkg in purchasable_packages()]
    farm = None
    try:
        farm = default_purchase_farm(profile)
    except ValueError:
        farm = None
    owned = PackagePurchase.objects.filter(
        user=profile,
        status__in=("paid", "allocated"),
        settled_at__isnull=True,
    ).count()
    can_purchase = bool(packages) and farm is not None
    block_message = ""
    if not packages:
        block_message = "No CGF package is open for purchase right now."
    elif farm is None:
        block_message = "No active goat farm is available for package purchases yet."
    return {
        "availableMain": float(available),
        "packages": packages,
        "defaultPackageId": packages[0]["id"] if packages else None,
        "farmName": farm.name if farm else "",
        "farmId": farm.pk if farm else None,
        "ownedActiveCount": owned,
        "canPurchase": can_purchase,
        "blockMessage": block_message,
        "hasProjectAccess": bool(profile.has_project(PROJECT_LABEL)),
    }


@transaction.atomic
def purchase_package_from_main_account(
    profile,
    *,
    package_id=None,
    quantity: int = 1,
    notes: str = "",
    created_by=None,
) -> dict[str, Any]:
    """Debit Main Account and create one or more active CGF package purchases."""
    if not profile.has_project(PROJECT_LABEL):
        raise ValueError("You do not have access to Commercial Goat Farming.")

    try:
        qty = int(quantity or 1)
    except (TypeError, ValueError):
        qty = 0
    if qty < 1:
        raise ValueError("Buy at least 1 CGF package.")
    if qty > 20:
        raise ValueError("You can buy up to 20 packages in one request.")

    packages = purchasable_packages()
    if not packages.exists():
        raise ValueError("No CGF package is open for purchase right now.")

    if package_id in ("", None):
        package = packages.first()
    else:
        try:
            package = packages.get(pk=int(package_id))
        except (TypeError, ValueError, InvestmentPackage.DoesNotExist):
            raise ValueError("That CGF package is not available for purchase.")

    amount = _q(package.total_cost) * qty
    if amount <= ZERO:
        raise ValueError("This package does not have a valid purchase price.")
    if amount > main_ledger.available_balance(profile):
        raise ValueError("Amount exceeds Main Account available balance.")

    farm = default_purchase_farm(profile)
    note_text = (notes or "").strip()
    description = (
        f"CGF purchase of {qty} × {package.name} "
        f"({package.goat_count} goats each) for UGX {amount:,.0f} from Main Account."
    )
    if note_text:
        description = f"{description} Note: {note_text}"

    main_tx = main_ledger.invest_to_project(
        profile,
        PROJECT_LABEL,
        amount,
        description=description,
        created_by=created_by or profile.user,
    )

    purchases: list[PackagePurchase] = []
    suffix_base = (main_tx.reference or "MAIN").replace(" ", "")[-12:]
    today = timezone.localdate()
    now = timezone.now()
    for index in range(qty):
        purchase = PackagePurchase.objects.create(
            user=profile,
            farm=farm,
            package=package,
            total_amount=_q(package.total_cost),
            amount_paid=ZERO,
            goats_allocated=0,
            status="pending",
            purchase_date=now,
            notes=note_text,
        )
        Payment.objects.create(
            purchase=purchase,
            amount=_q(package.total_cost),
            receipt_prefix=today.strftime("RCPT-%Y%m%d"),
            receipt_suffix=f"{suffix_base}-{index + 1:02d}",
            payment_method="Main Account",
            payment_date=today,
            notes=f"Paid from Main Account. Reference {main_tx.reference}.",
        )
        purchase.refresh_from_db()
        purchase.allocate_goats_to_accounts()
        purchase.refresh_from_db()
        purchases.append(purchase)

    goat_total = int(package.goat_count or 0) * qty
    MemberNotification.objects.create(
        user=profile.user,
        source=MemberNotification.Source.SYSTEM,
        title="CGF package purchased",
        body=(
            f"UGX {amount:,.0f} was moved from your Main Account to buy {qty} "
            f"{package.name} package{'s' if qty != 1 else ''} "
            f"({goat_total} female breeders). Receipt {main_tx.reference}."
        ),
    )
    return {
        "transaction": main_tx,
        "purchases": purchases,
        "package": package,
        "farm": farm,
        "quantity": qty,
        "amount": amount,
        "receipt": main_tx.reference,
        "notes": note_text,
        "options": build_purchase_options(profile),
    }


def _add_months(value, months: int):
    """Add whole calendar months while preserving date/datetime type and time."""
    if not value:
        return None
    months = max(1, int(months or DEFAULT_CGF_CYCLE_MONTHS))
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def cycle_duration_months_for_purchase(purchase) -> int:
    package = getattr(purchase, "package", None)
    months = getattr(package, "cycle_duration_months", None)
    try:
        return max(1, int(months or DEFAULT_CGF_CYCLE_MONTHS))
    except (TypeError, ValueError):
        return DEFAULT_CGF_CYCLE_MONTHS


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


def maturity_datetime(purchase_or_date):
    """Cycle end = purchase start + that package's configured cycle months."""
    purchase_date = getattr(purchase_or_date, "purchase_date", purchase_or_date)
    if not purchase_date:
        return None
    if hasattr(purchase_or_date, "purchase_date"):
        months = cycle_duration_months_for_purchase(purchase_or_date)
    else:
        months = DEFAULT_CGF_CYCLE_MONTHS
    return _add_months(purchase_date, months)


def is_purchase_matured(purchase, *, now=None) -> bool:
    now = now or timezone.now()
    matures = maturity_datetime(purchase)
    return bool(matures and matures <= now)


def cycle_progress_pct(purchase_or_date, *, now=None) -> int:
    """Elapsed time since purchase / configured package cycle, capped at 100."""
    purchase_date = getattr(purchase_or_date, "purchase_date", purchase_or_date)
    if not purchase_date:
        return 0
    now = now or timezone.now()
    elapsed = (now - purchase_date).total_seconds() / 86400.0
    if elapsed <= 0:
        return 0
    matures = maturity_datetime(purchase_or_date)
    if not matures:
        return 0
    total = max((matures - purchase_date).total_seconds() / 86400.0, 1)
    pct = int(round((elapsed / total) * 100))
    return max(0, min(100, pct))


def days_until_maturity(purchase_or_date, *, now=None) -> int | None:
    matures = maturity_datetime(purchase_or_date)
    if not matures:
        return None
    now = now or timezone.now()
    delta = (matures - now).total_seconds() / 86400.0
    return int(round(delta))


def eligible_cycle_queryset(profile=None, *, farm_id=None, unsettled_only=True):
    """Package purchases that participate in their package maturity cycle."""
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
    """Fully paid / allocated cycles past their package cycle that are not settled."""
    now = timezone.now()
    qs = eligible_cycle_queryset(profile, farm_id=farm_id, unsettled_only=True).filter(
        purchase_date__isnull=False
    )
    return [purchase for purchase in qs if is_purchase_matured(purchase, now=now)]


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
        return {
            "pct": 100,
            "next_maturity_at": maturity_datetime(
                min(matured, key=lambda p: (p.purchase_date, p.pk))
            )
            if matured
            else None,
            "matured_count": len(matured),
            "active_count": 0,
        }

    next_purchase = min(active, key=lambda p: (p.purchase_date, p.pk))
    return {
        "pct": cycle_progress_pct(next_purchase, now=now),
        "next_maturity_at": maturity_datetime(next_purchase),
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
            "cycle_duration_months": DEFAULT_CGF_CYCLE_MONTHS,
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
                "cycle_duration_months": DEFAULT_CGF_CYCLE_MONTHS,
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
            flags[farm_id]["next_maturity_at"] = maturity_datetime(next_p)
            flags[farm_id]["progress_pct"] = cycle_progress_pct(next_p, now=now)
            flags[farm_id]["cycle_duration_months"] = cycle_duration_months_for_purchase(next_p)
        elif matured:
            oldest = min(matured, key=lambda p: (p.purchase_date, p.pk))
            flags[farm_id]["cycle_start_at"] = oldest.purchase_date
            flags[farm_id]["next_maturity_at"] = maturity_datetime(oldest)
            flags[farm_id]["progress_pct"] = 100
            flags[farm_id]["cycle_duration_months"] = cycle_duration_months_for_purchase(oldest)

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
