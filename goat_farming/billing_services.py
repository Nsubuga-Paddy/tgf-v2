from __future__ import annotations

"""
billing_services.py (billing actions)

Responsibilities:
- Post a package charge (invoice) for a purchased package.
- Record a payment with a unique receipt number.
- Provide simple display dicts for UI.
- Compute next-year management fee from current herd size.
"""

from decimal import Decimal
from datetime import date

from django.db import transaction
from django.utils import timezone

from .models.herd import InvestmentPackage, ManagementFeeTier, FarmMembership
from .models.billing import PackageCharge, PackagePayment


@transaction.atomic
def post_package_charge(
    membership: FarmMembership,
    package: InvestmentPackage,
    due_date: date | None = None,
) -> PackageCharge:
    """
    Create a charge equal to (goat_count * goat_price_per_unit) + management_fee.
    This is the invoice the user pays against (fully or in parts).
    """
    total = (Decimal(package.goat_count) * package.goat_price_per_unit) + package.management_fee
    return PackageCharge.objects.create(
        membership=membership,
        package=package,
        total_amount=total,
        due_date=due_date,
        notes=f"{package.code} - {package.name}",
    )


@transaction.atomic
def record_package_payment(
    charge: PackageCharge,
    amount: Decimal,
    method: str = "MoMo",
    notes: str = "",
) -> PackagePayment:
    """
    Record a user payment against a specific package charge.
    A unique receipt_number is auto-generated in the model default.
    """
    if amount <= 0:
        raise ValueError("Payment amount must be positive.")
    return PackagePayment.objects.create(
        charge=charge,
        amount=amount,
        method=method,
        notes=notes,
    )


def package_charge_display(charge: PackageCharge) -> dict:
    """
    Produce a simple dict for UI cards/tables.
    """
    return {
        "reference": charge.reference,
        "package_code": charge.package.code,
        "package_name": charge.package.name,
        "total": charge.total_amount,
        "paid": charge.paid_amount,
        "balance": charge.balance,
        "status": charge.status,  # PENDING | PARTIAL | PAID
        "due_date": charge.due_date,
        "created_at": charge.created_at,
    }


def next_year_management_fee(membership: FarmMembership) -> dict:
    """
    Compute ONLY the annual management fee for the next year
    based on current goats (no package cost).
    """
    goats = membership.current_goats
    fee = ManagementFeeTier.fee_for_count(goats)
    return {
        "goats": goats,
        "annual_fee": fee,
    }
