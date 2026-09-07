from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from accounts.models import MemberNotification
from main_account import services as main_ledger
from main_account.models import MainAccountTransaction

from .emails import send_loan_disbursement_email
from .models import (
    DEFAULT_MONTHLY_INTEREST_RATE,
    LOAN_INSURANCE_FEE_RATE,
    LOAN_PROCESSING_FEE,
    MAX_BORROWING_LIMIT,
    MIN_BORROWING_AMOUNT,
    STAFF_MONTHLY_INTEREST_RATE,
    LoanApplication,
    LoanInstallment,
    LoanRepayment,
    MemberLoan,
)

TWO_PLACES = Decimal("0.01")
FOUR_PLACES = Decimal("0.0001")
ZERO = Decimal("0.00")
QUALIFYING_SAVINGS_AMOUNT = Decimal("1200000.00")
QUALIFYING_SAVINGS_DAYS = 365
ALLOWED_TERMS = {3, 6, 12, 18, 24}
PAYMENT_DETAILS = {
    "accountName": "MUSHANA FINANCE",
    "bankAccount": "01071118922629",
    "bankName": "DFCU Bank",
    "branch": "Jinja Road",
}


def q(amount) -> Decimal:
    return Decimal(amount or 0).quantize(TWO_PLACES)


def q_rate(value) -> Decimal:
    return Decimal(value or 0).quantize(FOUR_PLACES)


def generate_reference(prefix: str) -> str:
    return f"{prefix}-{timezone.now().year}-{uuid.uuid4().hex[:6].upper()}"


def purpose_label(value: str) -> str:
    return dict(LoanApplication.Purpose.choices).get(value, value)


def repayment_source_label(value: str) -> str:
    return dict(LoanApplication.RepaymentSource.choices).get(value, value)


def method_label(value: str) -> str:
    return dict(LoanRepayment.Method.choices).get(value, value)


def _notify(user, title: str, body: str) -> None:
    MemberNotification.objects.create(
        user=user,
        source=MemberNotification.Source.SYSTEM,
        title=title,
        body=body,
    )


def add_months(start: date, months: int) -> date:
    month = start.month - 1 + months
    year = start.year + month // 12
    month = month % 12 + 1
    days = [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return date(year, month, min(start.day, days[month - 1]))


def monthly_installment(principal: Decimal, months: int, monthly_rate: Decimal) -> Decimal:
    principal = q(principal)
    if months <= 0:
        raise ValueError("Loan term must be positive.")
    principal_part = q(principal / Decimal(months))
    monthly_interest = q(principal * monthly_rate)
    return q(principal_part + monthly_interest)


def loan_disbursement_breakdown(amount) -> dict[str, Decimal]:
    principal = q(amount)
    insurance_fee = q(principal * LOAN_INSURANCE_FEE_RATE)
    processing_fee = q(LOAN_PROCESSING_FEE)
    total_deductions = q(insurance_fee + processing_fee)
    net_disbursed = q(max(ZERO, principal - total_deductions))
    return {
        "principal": principal,
        "insurance_fee": insurance_fee,
        "processing_fee": processing_fee,
        "total_deductions": total_deductions,
        "net_disbursed_amount": net_disbursed,
    }


def create_installment_schedule(loan: MemberLoan) -> None:
    principal = q(loan.principal)
    principal_part = q(principal / Decimal(loan.term_months))
    monthly_interest = q(principal * loan.monthly_interest_rate)
    balance = q(loan.outstanding)
    rows = []
    for index in range(1, int(loan.term_months) + 1):
        if index == loan.term_months:
            principal_for_row = q(principal - (principal_part * Decimal(loan.term_months - 1)))
        else:
            principal_for_row = principal_part
        installment_total = q(principal_for_row + monthly_interest)
        balance = q(max(ZERO, balance - installment_total))
        rows.append(
            LoanInstallment(
                loan=loan,
                installment_number=index,
                due_date=add_months(loan.first_due_date, index - 1),
                principal_amount=principal_for_row,
                interest_amount=monthly_interest,
                total_amount=installment_total,
                balance_after=balance,
                status=LoanInstallment.Status.DUE if index == 1 else LoanInstallment.Status.UPCOMING,
            )
        )
    LoanInstallment.objects.bulk_create(rows)


def refresh_installment_statuses(loan: MemberLoan) -> None:
    installments = list(loan.installments.order_by("installment_number"))
    repaid = q(loan.repayments.aggregate_total if hasattr(loan.repayments, "aggregate_total") else ZERO)
    repaid = q(sum((payment.amount for payment in loan.repayments.all()), ZERO))
    paid_count = 0
    running = ZERO
    for installment in installments:
        running = q(running + installment.total_amount)
        if repaid >= running:
            installment.status = LoanInstallment.Status.PAID
            paid_count += 1
        elif paid_count == installment.installment_number - 1:
            installment.status = LoanInstallment.Status.DUE
        else:
            installment.status = LoanInstallment.Status.UPCOMING
    LoanInstallment.objects.bulk_update(installments, ["status"])
    loan.paid_installments = paid_count
    if loan.outstanding <= ZERO:
        loan.status = MemberLoan.Status.CLOSED
        loan.closed_date = timezone.localdate()
        for installment in installments:
            installment.status = LoanInstallment.Status.PAID
        LoanInstallment.objects.bulk_update(installments, ["status"])
        loan.paid_installments = len(installments)
    loan.save(update_fields=["paid_installments", "status", "closed_date", "updated_at"])


def rate_for_profile(profile) -> Decimal:
    if getattr(profile, "is_mcs_staff", False):
        return STAFF_MONTHLY_INTEREST_RATE
    return DEFAULT_MONTHLY_INTEREST_RATE


def rate_display_for_value(value) -> str:
    pct = (Decimal(value or 0) * Decimal("100")).quantize(Decimal("0.01"))
    return f"{pct.normalize()}% per month on principal"


def calculate_eligibility(profile) -> dict:
    user = profile.user
    missing_personal = []
    if not (user.first_name or "").strip():
        missing_personal.append("first name")
    if not (user.last_name or "").strip():
        missing_personal.append("last name")
    if not (user.email or "").strip():
        missing_personal.append("email")
    if not profile.whatsapp_number:
        missing_personal.append("WhatsApp number")
    if not (profile.national_id or "").strip():
        missing_personal.append("National ID")
    if not profile.birthdate:
        missing_personal.append("date of birth")
    personal_ready = not missing_personal

    bank_ready = bool(
        (profile.bank_name or "").strip()
        and (profile.bank_account_number or "").strip()
        and (profile.bank_account_name or "").strip()
    )
    has_active_projects = profile.projects.exists()
    has_shares = False
    share_value = ZERO
    try:
        from cooperative_shareholding.services import build_shareholding_summary

        summary = build_shareholding_summary(profile.user.cooperative_shareholding)
        share_value = q(summary.get("portfolio_value") or ZERO)
        has_shares = share_value > ZERO
    except Exception:
        share_value = ZERO

    main_posted = main_ledger.posted_balance(profile)
    try:
        savings_total = q(profile.get_amount_saved())
    except Exception:
        savings_total = ZERO
    first_deposit = None
    try:
        first_deposit = (
            profile.savings_transactions.filter(transaction_type="deposit")
            .order_by("transaction_date", "created_at")
            .first()
        )
    except Exception:
        first_deposit = None
    cutoff = timezone.localdate() - timedelta(days=QUALIFYING_SAVINGS_DAYS)
    has_one_year_savings = bool(first_deposit and first_deposit.transaction_date <= cutoff)
    has_savings_amount = savings_total >= QUALIFYING_SAVINGS_AMOUNT
    has_savings = has_one_year_savings and has_savings_amount
    has_project_or_savings = has_active_projects or has_savings or savings_total > ZERO
    has_overdue = profile.member_loans.filter(status=MemberLoan.Status.OVERDUE).exists()
    is_verified = bool(profile.is_verified)
    is_staff = bool(getattr(profile, "is_mcs_staff", False))
    suggested_rate = rate_for_profile(profile)

    # Hard blockers only: verification, personal details, and bank details.
    hard_blockers = []
    if not is_verified:
        hard_blockers.append(
            {
                "id": "membership",
                "label": "Platform verification is pending",
                "detail": "Your MCS account must be verified before you can submit a loan application.",
                "ctaLabel": "View verification status",
                "ctaTo": "/verification-pending",
            }
        )
    if not personal_ready:
        hard_blockers.append(
            {
                "id": "personal",
                "label": "Complete your personal details",
                "detail": f"Missing: {', '.join(missing_personal)}.",
                "ctaLabel": "Complete your profile",
                "ctaTo": "/profile",
            }
        )
    if not bank_ready:
        hard_blockers.append(
            {
                "id": "bank",
                "label": "Add your bank account details",
                "detail": "Bank name, account number, and account name are required for loan disbursement records.",
                "ctaLabel": "Complete bank details",
                "ctaTo": "/profile",
            }
        )
    core_ready = not hard_blockers

    factors = [
        {
            "id": "membership",
            "label": "Verified MCS membership",
            "met": is_verified,
            "soft": False,
            "detail": "Your account is verified" if is_verified else "Complete verification first",
        },
        {
            "id": "personal",
            "label": "Complete personal details",
            "met": personal_ready,
            "soft": False,
            "detail": "Required personal details are complete" if personal_ready else f"Missing: {', '.join(missing_personal)}",
        },
        {
            "id": "bank",
            "label": "Bank account details",
            "met": bank_ready,
            "soft": False,
            "detail": "Bank details on file for disbursement" if bank_ready else "Add bank name, account number, and account name",
        },
    ]
    if is_staff:
        factors.append(
            {
                "id": "staff",
                "label": "MCS staff loan terms",
                "met": True,
                "soft": True,
                "detail": "Staff interest rate: 1% per month on principal",
            }
        )
    factors.extend(
        [
            {
                "id": "shares",
                "label": "Cooperative shareholding",
                "met": has_shares,
                "soft": True,
                "detail": (
                    f"Portfolio value UGX {int(share_value):,}"
                    if has_shares
                    else "No shareholding on record yet — the committee may still review your application"
                ),
            },
            {
                "id": "project_or_savings",
                "label": "Project participation or savings",
                "met": has_project_or_savings,
                "soft": True,
                "detail": (
                    (
                        "Active project access"
                        if has_active_projects
                        else "No active project access"
                    )
                    + (
                        f"; savings UGX {int(savings_total):,}"
                        if savings_total > ZERO
                        else "; no savings balance yet"
                    )
                ),
            },
            {
                "id": "savings_history",
                "label": "Qualifying savings history",
                "met": has_savings,
                "soft": True,
                "detail": (
                    f"At least 1 year of savings and UGX {int(savings_total):,} saved"
                    if has_savings
                    else f"Stronger cases usually show ~1 year of savings and at least UGX {int(QUALIFYING_SAVINGS_AMOUNT):,}"
                ),
            },
            {
                "id": "repayment",
                "label": "Good repayment history",
                "met": not has_overdue,
                "soft": True,
                "detail": "Clear overdue loan payments first" if has_overdue else "No overdue MCS loans",
            },
            {
                "id": "profile",
                "label": "Committee review",
                "met": None,
                "soft": True,
                "detail": "Shareholding, project participation/savings, and repayment history guide committee decisions.",
            },
        ]
    )
    status = "not_eligible"
    status_label = "Not eligible yet"
    apply_enabled = False
    soft_strong = has_shares and has_project_or_savings and not has_overdue
    if core_ready and soft_strong:
        status = "eligible"
        status_label = "Eligible to apply"
        apply_enabled = True
    elif core_ready:
        status = "may_qualify"
        status_label = "You may apply - committee review required"
        apply_enabled = True
    elif is_verified:
        status_label = "Not ready to apply"

    raw_cap = max(share_value * Decimal("0.6"), main_posted + Decimal("2000000.00"), Decimal("3000000.00"))
    estimated = min(MAX_BORROWING_LIMIT, q(raw_cap))
    first_blocker = hard_blockers[0] if hard_blockers else None
    if is_staff:
        if status == "eligible":
            summary = (
                "As MCS staff, your suggested interest rate is 1% per month on principal. "
                "You meet the core MCS lending checks and may apply for up to UGX 10,000,000 subject to committee approval."
            )
        elif status == "may_qualify":
            summary = (
                "As MCS staff, your suggested interest rate is 1% per month on principal. "
                "You can submit a loan application. Shareholding and project participation/savings will be reviewed by the committee."
            )
        else:
            summary = "Complete the required items below before applying for cooperative credit."
        applicant_type = "MCS staff"
    else:
        if status == "eligible":
            summary = (
                "You meet the core MCS lending checks and may apply for up to UGX 10,000,000 subject to committee approval."
            )
        elif status == "may_qualify":
            summary = (
                "You can submit a loan application. Shareholding and project participation/savings will be reviewed by the committee."
            )
        else:
            summary = "Complete the required items below before applying for cooperative credit."
        applicant_type = "Member"
    return {
        "status": status,
        "statusLabel": status_label,
        "applicantType": applicant_type if is_staff else None,
        "isStaff": is_staff,
        "suggestedMonthlyRate": float(suggested_rate),
        "rateDisplay": rate_display_for_value(suggested_rate),
        "summary": summary,
        "estimatedMaxAmount": int(estimated) if estimated > ZERO else None,
        "estimatedMaxLabel": "Maximum borrowing limit",
        "applyEnabled": apply_enabled,
        "applyMessage": "Submit an application for credit committee review." if apply_enabled else "Complete the hard-blocking items before applying.",
        "blockers": hard_blockers,
        "ctaLabel": first_blocker["ctaLabel"] if first_blocker else "Continue to application",
        "ctaTo": first_blocker["ctaTo"] if first_blocker else "/loans/apply",
        "factors": factors,
        "checkedAt": timezone.now().isoformat(),
    }


def create_application(profile, *, purpose, amount, term_months, repayment_source, notes="") -> LoanApplication:
    amount = q(amount)
    term_months = int(term_months)
    if amount < MIN_BORROWING_AMOUNT:
        raise ValueError("Minimum loan amount is UGX 100,000.")
    if amount > MAX_BORROWING_LIMIT:
        raise ValueError("Maximum borrowing limit is UGX 10,000,000.")
    if term_months not in ALLOWED_TERMS:
        raise ValueError("Choose a supported repayment term.")
    if purpose not in dict(LoanApplication.Purpose.choices):
        raise ValueError("Choose a valid loan purpose.")
    if repayment_source not in dict(LoanApplication.RepaymentSource.choices):
        raise ValueError("Choose a valid repayment source.")
    eligibility = calculate_eligibility(profile)
    if not eligibility.get("applyEnabled"):
        raise ValueError(eligibility.get("applyMessage") or "You are not eligible to apply yet.")
    app = LoanApplication.objects.create(
        user_profile=profile,
        reference=generate_reference("LA"),
        purpose=purpose,
        amount_requested=amount,
        term_months=term_months,
        repayment_source=repayment_source,
        notes=notes or "",
        monthly_interest_rate=rate_for_profile(profile),
    )
    _notify(
        profile.user,
        "Loan application submitted",
        f"Your loan application {app.reference} has been received for credit committee review.",
    )
    return app


def approval_blockers(application: LoanApplication) -> list[str]:
    blockers: list[str] = []

    if application.status == LoanApplication.Status.DISBURSED:
        blockers.append("This application has already been disbursed.")
    if application.status == LoanApplication.Status.REJECTED:
        blockers.append("Rejected applications cannot be disbursed.")
    if MemberLoan.objects.filter(application=application).exists():
        blockers.append("A member loan already exists for this application.")

    try:
        amount = q(application.approved_amount or application.amount_requested)
    except Exception:
        amount = ZERO
        blockers.append("Approved amount is invalid.")
    try:
        term = int(application.approved_term_months or application.term_months)
    except (TypeError, ValueError):
        term = 0
        blockers.append("Approved term is invalid.")
    try:
        rate = q_rate(application.monthly_interest_rate or DEFAULT_MONTHLY_INTEREST_RATE)
    except Exception:
        rate = ZERO
        blockers.append("Monthly interest rate is invalid.")

    if amount <= ZERO:
        blockers.append("Approved amount must be positive.")
    elif amount < MIN_BORROWING_AMOUNT:
        blockers.append("Approved amount is below the UGX 100,000 minimum.")
    elif amount > MAX_BORROWING_LIMIT:
        blockers.append("Approved amount exceeds the UGX 10,000,000 borrowing limit.")

    if term not in ALLOWED_TERMS:
        supported = ", ".join(str(months) for months in sorted(ALLOWED_TERMS))
        blockers.append(
            f"Approved term {term or 'blank'} months is not supported. Choose one of: {supported} months."
        )

    if rate < ZERO:
        blockers.append("Monthly interest rate cannot be negative.")

    eligibility = calculate_eligibility(application.user_profile)
    for blocker in eligibility.get("blockers") or []:
        label = blocker.get("label") or "Eligibility blocker"
        detail = blocker.get("detail") or ""
        blockers.append(f"{label}: {detail}".strip())

    return blockers


@transaction.atomic
def approve_and_disburse(application: LoanApplication, *, admin=None, note: str = "") -> MemberLoan:
    app = LoanApplication.objects.select_for_update().select_related("user_profile", "user_profile__user").get(pk=application.pk)
    blockers = approval_blockers(app)
    if blockers:
        raise ValueError(" ".join(blockers))
    if app.status == LoanApplication.Status.DISBURSED:
        if hasattr(app, "loan"):
            return app.loan
        raise ValueError("This application is already marked as disbursed.")
    if app.status == LoanApplication.Status.REJECTED:
        raise ValueError("Rejected applications cannot be disbursed.")

    amount = q(app.approved_amount or app.amount_requested)
    term = int(app.approved_term_months or app.term_months)
    rate = q_rate(app.monthly_interest_rate or DEFAULT_MONTHLY_INTEREST_RATE)
    if amount <= ZERO:
        raise ValueError("Approved amount must be positive.")
    if amount < MIN_BORROWING_AMOUNT:
        raise ValueError("Approved amount is below the UGX 100,000 minimum.")
    if amount > MAX_BORROWING_LIMIT:
        raise ValueError("Approved amount exceeds the UGX 10,000,000 borrowing limit.")
    if term not in ALLOWED_TERMS:
        raise ValueError("Approved term is not supported.")

    today = timezone.localdate()
    installment = monthly_installment(amount, term, rate)
    total_repayable = q(amount + (amount * rate * Decimal(term)))
    fee_breakdown = loan_disbursement_breakdown(amount)
    loan = MemberLoan.objects.create(
        user_profile=app.user_profile,
        application=app,
        reference=generate_reference("LN"),
        purpose=app.purpose,
        principal=amount,
        insurance_fee=fee_breakdown["insurance_fee"],
        processing_fee=fee_breakdown["processing_fee"],
        total_deductions=fee_breakdown["total_deductions"],
        net_disbursed_amount=fee_breakdown["net_disbursed_amount"],
        outstanding=total_repayable,
        monthly_interest_rate=rate,
        term_months=term,
        installment_amount=installment,
        disbursed_date=today,
        first_due_date=add_months(today, 1),
        created_by=admin,
    )
    tx = main_ledger.post_transaction(
        app.user_profile,
        direction=MainAccountTransaction.Direction.CREDIT,
        category=MainAccountTransaction.Category.LOAN_DISBURSEMENT,
        amount=fee_breakdown["net_disbursed_amount"],
        source_label=f"Loan disbursement {loan.reference}",
        description=(
            f"Approved loan application {app.reference} credited to Main Account after "
            f"UGX {fee_breakdown['total_deductions']:,.0f} deductions "
            f"(insurance UGX {fee_breakdown['insurance_fee']:,.0f}, "
            f"processing UGX {fee_breakdown['processing_fee']:,.0f})."
        ),
        created_by=admin,
        reference_prefix="LND",
    )
    loan.disbursement_transaction = tx
    loan.save(update_fields=["disbursement_transaction", "updated_at"])
    create_installment_schedule(loan)

    app.status = LoanApplication.Status.DISBURSED
    app.approved_amount = amount
    app.approved_term_months = term
    app.monthly_interest_rate = rate
    app.committee_note = note or app.committee_note
    app.decided_by = admin
    app.reviewed_at = app.reviewed_at or timezone.now()
    app.disbursed_at = timezone.now()
    app.save(
        update_fields=[
            "status",
            "approved_amount",
            "approved_term_months",
            "monthly_interest_rate",
            "committee_note",
            "decided_by",
            "reviewed_at",
            "disbursed_at",
            "updated_at",
        ]
    )
    _notify(
        app.user_profile.user,
        "Loan approved and disbursed",
        (
            f"{loan.reference} has been credited to your Main Account. "
            f"Approved amount: UGX {amount:,.0f}. "
            f"Deductions: UGX {fee_breakdown['total_deductions']:,.0f} "
            f"(insurance UGX {fee_breakdown['insurance_fee']:,.0f}, "
            f"processing UGX {fee_breakdown['processing_fee']:,.0f}). "
            f"Net credited: UGX {fee_breakdown['net_disbursed_amount']:,.0f}. "
            f"Term: {term} months at {rate_display_for_value(rate)}. "
            f"Monthly installment: UGX {installment:,.0f}. "
            f"Total repayable: UGX {total_repayable:,.0f}. "
            f"First installment due: {loan.first_due_date.strftime('%d %b %Y')}. "
            f"Open Loans to view your full repayment schedule."
        ),
    )
    send_loan_disbursement_email(loan)
    return loan


def reject_application(application: LoanApplication, *, admin=None, reason: str = "") -> LoanApplication:
    if application.status == LoanApplication.Status.DISBURSED:
        raise ValueError("Disbursed applications cannot be rejected.")
    already_rejected = application.status == LoanApplication.Status.REJECTED
    rejection_reason = (reason or application.rejection_reason or "").strip()
    application.status = LoanApplication.Status.REJECTED
    application.rejection_reason = rejection_reason
    application.decided_by = admin
    application.reviewed_at = timezone.now()
    application.save(update_fields=["status", "rejection_reason", "decided_by", "reviewed_at", "updated_at"])
    body = f"Your loan application {application.reference} was not approved."
    if rejection_reason:
        body = f"{body} Reason: {rejection_reason}"
    if not already_rejected:
        _notify(
            application.user_profile.user,
            "Loan application update",
            body,
        )
    return application


def _apply_repayment(loan: MemberLoan, amount: Decimal) -> None:
    loan.outstanding = q(max(ZERO, q(loan.outstanding) - amount))
    loan.save(update_fields=["outstanding", "updated_at"])
    refresh_installment_statuses(loan)


@transaction.atomic
def repay_from_main_account(profile, loan_id, amount, *, notes: str = "") -> LoanRepayment:
    amount = q(amount)
    if amount <= ZERO:
        raise ValueError("Enter a valid repayment amount.")
    loan = MemberLoan.objects.select_for_update().get(pk=loan_id, user_profile=profile)
    if loan.status not in {MemberLoan.Status.ACTIVE, MemberLoan.Status.OVERDUE}:
        raise ValueError("Only active loans can be repaid.")
    if amount > loan.outstanding:
        raise ValueError("Amount exceeds outstanding loan balance.")
    if amount > main_ledger.available_balance(profile):
        raise ValueError("Amount exceeds Main Account available balance.")
    note_text = (notes or "").strip()
    outstanding_after = q(max(ZERO, q(loan.outstanding) - amount))
    description = f"Repayment from Main Account to loan {loan.reference}."
    if note_text:
        description = f"{description} Note: {note_text}"
    tx = main_ledger.post_transaction(
        profile,
        direction=MainAccountTransaction.Direction.DEBIT,
        category=MainAccountTransaction.Category.LOAN_REPAYMENT,
        amount=amount,
        source_label=f"Loan repayment {loan.reference}",
        description=description,
        created_by=profile.user,
        reference_prefix="LNR",
    )
    repayment = LoanRepayment.objects.create(
        loan=loan,
        amount=amount,
        outstanding_after=outstanding_after,
        method=LoanRepayment.Method.MAIN_ACCOUNT,
        reference=generate_reference("LR"),
        main_account_transaction=tx,
        notes=note_text,
        posted_by=profile.user,
    )
    _apply_repayment(loan, amount)
    _notify(
        profile.user,
        "Loan repayment posted",
        f"UGX {amount:,.0f} was repaid from your Main Account to {loan.reference}.",
    )
    return repayment


@transaction.atomic
def record_bank_repayment(
    loan: MemberLoan,
    amount,
    *,
    external_reference: str = "",
    receipt=None,
    notes: str = "",
    posted_by=None,
) -> LoanRepayment:
    amount = q(amount)
    loan = MemberLoan.objects.select_for_update().get(pk=loan.pk)
    if amount <= ZERO:
        raise ValueError("Repayment amount must be positive.")
    if loan.status not in {MemberLoan.Status.ACTIVE, MemberLoan.Status.OVERDUE}:
        raise ValueError("Only active loans can receive repayments.")
    if amount > loan.outstanding:
        raise ValueError("Amount exceeds outstanding loan balance.")
    outstanding_after = q(max(ZERO, q(loan.outstanding) - amount))
    repayment = LoanRepayment.objects.create(
        loan=loan,
        amount=amount,
        outstanding_after=outstanding_after,
        method=LoanRepayment.Method.BANK_TRANSFER,
        reference=generate_reference("LR"),
        external_reference=(external_reference or "").strip(),
        receipt=receipt,
        notes=notes or "",
        posted_by=posted_by,
    )
    _apply_repayment(loan, amount)
    _notify(
        loan.user_profile.user,
        "Bank loan repayment posted",
        f"MCS staff posted your bank transfer repayment of UGX {amount:,.0f} to {loan.reference}.",
    )
    return repayment
