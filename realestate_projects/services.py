from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from accounts.models import MemberNotification
from main_account import services as main_ledger

from .models import (
    RealEstateProject,
    RealEstateProjectActionRequest,
    RealEstateProjectTransaction,
)

TWO_PLACES = Decimal("0.01")
ZERO = Decimal("0.00")
PROJECT_LABEL = "Real Estate Projects"


def _q(amount) -> Decimal:
    return Decimal(amount or 0).quantize(TWO_PLACES)


def paid_amount(user, project) -> Decimal:
    total = ZERO
    for txn in RealEstateProjectTransaction.objects.filter(user=user, project=project):
        if txn.type in (
            RealEstateProjectTransaction.TYPE_PAYMENT,
            RealEstateProjectTransaction.TYPE_ADJUSTMENT,
        ):
            total += txn.amount
        elif txn.type == RealEstateProjectTransaction.TYPE_REFUND:
            total -= txn.amount
    return total if total > ZERO else ZERO


def _action_request_qs():
    """Avoid selecting optional FK columns that may not exist before migrate."""
    return RealEstateProjectActionRequest.objects.defer(
        "main_account_transaction",
        "realestate_transaction",
        "processed_by",
    )


def pending_refund_total(user, project, *, exclude_request=None) -> Decimal:
    qs = _action_request_qs().filter(
        user=user,
        project=project,
        action_type=RealEstateProjectActionRequest.ACTION_REFUND,
        status__in=[
            RealEstateProjectActionRequest.STATUS_PENDING,
            RealEstateProjectActionRequest.STATUS_APPROVED,
        ],
    )
    if exclude_request is not None and exclude_request.pk:
        qs = qs.exclude(pk=exclude_request.pk)
    return _q(qs.aggregate(total=Sum("amount"))["total"] or ZERO)


def refundable_amount(user, project, *, exclude_request=None) -> Decimal:
    amount = paid_amount(user, project) - pending_refund_total(
        user,
        project,
        exclude_request=exclude_request,
    )
    return amount if amount > ZERO else ZERO


def create_refund_request(user, project, *, amount=None, reason=""):
    if not project.allowed_members.filter(pk=user.pk).exists():
        raise ValueError("You do not have access to this Real Estate project.")

    profile = getattr(user, "profile", None)
    if profile is None:
        raise ValueError("Member profile is missing. Please contact support.")
    bank_ok = bool(
        (profile.bank_name or "").strip()
        and (profile.bank_account_number or "").strip()
        and (profile.bank_account_name or "").strip()
    )
    if not bank_ok:
        raise ValueError(
            "Add your full bank account details on your profile before requesting a refund."
        )

    available = refundable_amount(user, project)
    requested = _q(amount if amount not in (None, "") else available)
    if requested <= ZERO:
        raise ValueError("There is no refundable amount available for this project.")
    if requested > available:
        raise ValueError("Requested refund exceeds the available refundable amount.")

    return RealEstateProjectActionRequest.objects.create(
        user=user,
        project=project,
        action_type=RealEstateProjectActionRequest.ACTION_REFUND,
        amount=requested,
        available_at_request=available,
        reason=reason,
        status=RealEstateProjectActionRequest.STATUS_PENDING,
    )


@transaction.atomic
def process_refund_request(action_request, *, admin=None, admin_notes=""):
    """Credit Main Account only after explicit admin approval/processing.

    Pending requests must never credit the Main Account. Funds stay held against
    the Real Estate project until this function runs successfully.
    """
    req = RealEstateProjectActionRequest.objects.select_for_update().get(pk=action_request.pk)
    if req.action_type != RealEstateProjectActionRequest.ACTION_REFUND:
        raise ValueError("Only refund requests can be processed by this action.")
    if req.main_account_transaction_id:
        raise ValueError("This refund was already credited to the Main Account.")
    if req.status not in {
        RealEstateProjectActionRequest.STATUS_PENDING,
        RealEstateProjectActionRequest.STATUS_APPROVED,
    }:
        raise ValueError("Only pending or approved refund requests can be credited.")

    available = refundable_amount(req.user, req.project, exclude_request=req)
    amount = _q(req.amount)
    if amount <= ZERO:
        raise ValueError("Refund amount must be positive.")
    if amount > available:
        raise ValueError("Refund amount exceeds the member's current refundable balance.")

    project_tx = RealEstateProjectTransaction.objects.create(
        project=req.project,
        user=req.user,
        amount=amount,
        type=RealEstateProjectTransaction.TYPE_REFUND,
        payment_status=RealEstateProjectTransaction.PAYMENT_STATUS_PARTIAL,
        note=admin_notes or "Refund credited to Main Account",
        transaction_date=timezone.localdate(),
    )
    main_tx = main_ledger.transfer_from_project(
        req.user.profile,
        f"Real Estate refund - {req.project.name}",
        amount,
        description=admin_notes or f"Refund from {req.project.name}",
        created_by=admin,
    )

    req.status = RealEstateProjectActionRequest.STATUS_PROCESSED
    req.realestate_transaction = project_tx
    req.main_account_transaction = main_tx
    req.processed_by = admin
    req.admin_notes = admin_notes or "Refund credited to Main Account"
    req.processed_at = timezone.now()
    req.save()
    return req


def approve_refund_request(action_request, *, admin=None, admin_notes=""):
    """Approve a refund and credit the member's Main Account."""
    return process_refund_request(
        action_request,
        admin=admin,
        admin_notes=admin_notes or "Refund credited to Main Account",
    )


@transaction.atomic
def reverse_premature_refund_credit(action_request, *, admin=None, admin_notes=""):
    """Undo a Main Account credit that was posted before proper approval."""
    from main_account.models import MainAccountTransaction
    from main_account.services import post_transaction

    req = RealEstateProjectActionRequest.objects.select_for_update().get(pk=action_request.pk)
    if req.action_type != RealEstateProjectActionRequest.ACTION_REFUND:
        raise ValueError("Only refund requests can be reversed by this action.")
    if not req.main_account_transaction_id:
        raise ValueError("This refund has no Main Account credit to reverse.")

    amount = _q(req.amount)
    post_transaction(
        req.user.profile,
        direction=MainAccountTransaction.Direction.DEBIT,
        category=MainAccountTransaction.Category.ADJUSTMENT,
        amount=amount,
        source_label=f"Reversal of refund credit - {req.project.name}",
        description=admin_notes
        or "Premature refund credit reversed. Amount held until administrator approves.",
        created_by=admin,
        reference_prefix="REV",
    )

    if req.realestate_transaction_id:
        RealEstateProjectTransaction.objects.filter(pk=req.realestate_transaction_id).delete()

    req.status = RealEstateProjectActionRequest.STATUS_PENDING
    req.realestate_transaction = None
    req.main_account_transaction = None
    req.processed_by = None
    req.processed_at = None
    req.admin_notes = admin_notes or (
        "Premature Main Account credit reversed. Refund remains pending approval."
    )
    req.save()
    return req


def reject_refund_request(action_request, *, admin=None, admin_notes=""):
    if action_request.action_type != RealEstateProjectActionRequest.ACTION_REFUND:
        raise ValueError("Only refund requests can be rejected by this action.")
    if action_request.status not in {
        RealEstateProjectActionRequest.STATUS_PENDING,
        RealEstateProjectActionRequest.STATUS_APPROVED,
    }:
        raise ValueError("Only pending or approved refund requests can be rejected.")
    if action_request.main_account_transaction_id:
        raise ValueError(
            "This refund was already credited. Reverse the Main Account credit before rejecting."
        )
    action_request.status = RealEstateProjectActionRequest.STATUS_REJECTED
    action_request.processed_by = admin
    action_request.admin_notes = admin_notes
    action_request.processed_at = timezone.now()
    action_request.save()
    return action_request


def investable_projects(user):
    """Running Real Estate projects the member already has access to."""
    return (
        RealEstateProject.objects.filter(
            status=RealEstateProject.STATUS_RUNNING,
            allowed_members=user,
        )
        .distinct()
        .order_by("name", "pk")
    )


def _rep_date_label(value) -> str:
    if not value:
        return ""
    return f"{value.day} {value.strftime('%b %Y')}"


def serialize_investable_project(user, project) -> dict:
    paid = paid_amount(user, project)
    unit = (project.land_size_unit or "").strip()
    land_size_label = ""
    if project.land_size is not None:
        land_size_label = f"{project.land_size:g} {unit}".strip()
    return {
        "id": project.pk,
        "name": project.name,
        "location": project.location or "",
        "description": (project.description or "").strip(),
        "status": project.status,
        "startDate": _rep_date_label(project.start_date),
        "endDate": _rep_date_label(project.end_date),
        "minimumInvestment": project.minimum_investment or "",
        "landSize": float(project.land_size) if project.land_size is not None else None,
        "landSizeUnit": unit,
        "landSizeLabel": land_size_label,
        "alreadyPaid": float(paid),
    }


def build_contribute_options(profile) -> dict:
    user = profile.user
    available = main_ledger.available_balance(profile)
    projects = [serialize_investable_project(user, project) for project in investable_projects(user)]
    can_contribute = bool(projects)
    block_message = ""
    if not can_contribute:
        block_message = (
            "You do not have an open Real Estate project to pay into yet. "
            "Join a running project first."
        )
    return {
        "availableMain": float(available),
        "projects": projects,
        "defaultProjectId": projects[0]["id"] if projects else None,
        "canContribute": can_contribute,
        "blockMessage": block_message,
        "hasProjectAccess": bool(profile.has_project(PROJECT_LABEL)),
    }


@transaction.atomic
def contribute_from_main_account(
    profile,
    *,
    project_id,
    amount,
    notes: str = "",
    created_by=None,
) -> dict:
    if not profile.has_project(PROJECT_LABEL):
        raise ValueError("You do not have access to Real Estate Projects.")

    try:
        project = investable_projects(profile.user).get(pk=int(project_id))
    except (TypeError, ValueError, RealEstateProject.DoesNotExist):
        raise ValueError(
            "Select a running Real Estate project you already have access to."
        )

    amount = _q(amount)
    if amount <= ZERO:
        raise ValueError("Enter a valid contribution amount.")
    if amount > main_ledger.available_balance(profile):
        raise ValueError("Amount exceeds Main Account available balance.")

    note_text = (notes or "").strip()
    description = (
        f"Real Estate contribution of UGX {amount:,.0f} to {project.name} from Main Account."
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
    paid_after = paid_amount(profile.user, project) + amount
    project_tx = RealEstateProjectTransaction.objects.create(
        project=project,
        user=profile.user,
        amount=amount,
        type=RealEstateProjectTransaction.TYPE_PAYMENT,
        payment_status=RealEstateProjectTransaction.PAYMENT_STATUS_PARTIAL,
        note=note_text or f"Paid from Main Account. Receipt {main_tx.reference}.",
        transaction_date=timezone.localdate(),
    )
    MemberNotification.objects.create(
        user=profile.user,
        source=MemberNotification.Source.SYSTEM,
        title="Real Estate contribution posted",
        body=(
            f"UGX {amount:,.0f} was moved from your Main Account into {project.name}. "
            f"Receipt {main_tx.reference}."
        ),
    )
    return {
        "transaction": main_tx,
        "project_transaction": project_tx,
        "project": project,
        "amount": amount,
        "receipt": main_tx.reference,
        "already_paid": paid_after,
        "notes": note_text,
        "options": build_contribute_options(profile),
    }
