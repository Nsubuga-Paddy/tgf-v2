from __future__ import annotations

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from main_account import services as main_ledger

from .emails import (
    send_loan_autodebit_failed_email,
    send_loan_overdue_email,
    send_loan_overdue_reminder_email,
    send_loan_staff_arrears_digest_email,
)
from .models import LoanInstallment, LoanOpsState, LoanRepayment, MemberLoan
from .services import (
    _notify,
    add_months,
    last_scheduled_due,
    q,
    repay_from_main_account,
    sync_open_loan,
    ZERO,
)


def notify_member_overdue(loan: MemberLoan, today=None) -> str:
    """Send first overdue notice or the monthly reminder. Returns the notice type or ''."""
    today = today or timezone.localdate()
    if loan.status != MemberLoan.Status.OVERDUE:
        return ""
    now = timezone.now()
    if not loan.first_overdue_notice_at:
        send_loan_overdue_email(loan)
        _notify(
            loan.user_profile.user,
            "Loan payment overdue",
            (
                f"{loan.reference} is overdue. Outstanding balance is UGX {q(loan.outstanding):,.0f}. "
                f"New loan applications are blocked until this loan is fully paid. "
                f"Interest continues at {loan.rate_display} on the original principal until cleared."
            ),
        )
        loan.first_overdue_notice_at = now
        loan.last_member_reminder_at = now
        loan.save(
            update_fields=["first_overdue_notice_at", "last_member_reminder_at", "updated_at"]
        )
        return "first"
    last = timezone.localdate(loan.last_member_reminder_at) if loan.last_member_reminder_at else None
    if last and add_months(last, 1) <= today:
        send_loan_overdue_reminder_email(loan)
        _notify(
            loan.user_profile.user,
            "Loan overdue reminder",
            (
                f"{loan.reference} is still overdue. Outstanding balance is UGX {q(loan.outstanding):,.0f}, "
                f"including UGX {q(loan.arrears_interest):,.0f} continuing interest. "
                f"Please repay from Main Account or by bank transfer."
            ),
        )
        loan.last_member_reminder_at = now
        loan.save(update_fields=["last_member_reminder_at", "updated_at"])
        return "monthly"
    return ""


@transaction.atomic
def attempt_auto_debit(loan: MemberLoan, today=None) -> str:
    """Try one installment debit. Returns 'paid', 'failed', or ''."""
    today = today or timezone.localdate()
    if not loan.auto_debit:
        return ""
    if loan.status not in {MemberLoan.Status.ACTIVE, MemberLoan.Status.OVERDUE}:
        return ""
    if q(loan.outstanding) <= ZERO:
        return ""
    if loan.last_auto_debit_at == today:
        return ""
    installment = (
        loan.installments.filter(auto_debit_attempted_on__isnull=True, due_date__lte=today)
        .exclude(status=LoanInstallment.Status.PAID)
        .order_by("due_date", "installment_number")
        .first()
    )
    last_due = last_scheduled_due(loan)
    if installment is None:
        if not (last_due and last_due <= today and q(loan.outstanding) > ZERO):
            return ""
        if loan.last_auto_debit_at and add_months(loan.last_auto_debit_at, 1) > today:
            return ""
        amount = q(min(q(loan.installment_amount), q(loan.outstanding)))
    else:
        amount = q(min(q(installment.total_amount), q(loan.outstanding)))

    if amount <= ZERO:
        if installment is not None:
            installment.auto_debit_attempted_on = today
            installment.save(update_fields=["auto_debit_attempted_on"])
        return ""

    profile = loan.user_profile
    available = q(main_ledger.available_balance(profile))
    loan.last_auto_debit_at = today
    if installment is not None:
        installment.auto_debit_attempted_on = today
        installment.save(update_fields=["auto_debit_attempted_on"])

    if available < amount:
        loan.last_auto_debit_failure_at = timezone.now()
        loan.save(update_fields=["last_auto_debit_at", "last_auto_debit_failure_at", "updated_at"])
        send_loan_autodebit_failed_email(loan, amount=amount, available=available)
        _notify(
            profile.user,
            "Loan auto-debit failed",
            (
                f"MCS could not debit UGX {amount:,.0f} from your Main Account for {loan.reference} "
                f"because the available balance is UGX {available:,.0f}. "
                "Please add funds or repay another way. Interest continues if the installment stays unpaid."
            ),
        )
        return "failed"

    loan.save(update_fields=["last_auto_debit_at", "updated_at"])
    repay_from_main_account(
        profile,
        loan.pk,
        amount,
        notes="Automatic monthly Main Account debit.",
        method=LoanRepayment.Method.AUTO_DEBIT,
    )
    return "paid"


def send_staff_digest_if_due(today=None) -> bool:
    today = today or timezone.localdate()
    overdue_loans = list(
        MemberLoan.objects.filter(status=MemberLoan.Status.OVERDUE)
        .select_related("user_profile", "user_profile__user")
        .order_by("overdue_since", "reference")
    )
    if not overdue_loans:
        return False
    state = LoanOpsState.get_solo()
    if state.last_staff_digest_on and add_months(state.last_staff_digest_on, 1) > today:
        return False
    recipients = [
        email.strip()
        for email in getattr(settings, "LOAN_STAFF_EMAILS", [])
        if str(email).strip()
    ]
    if not recipients:
        return False
    sent = send_loan_staff_arrears_digest_email(overdue_loans, recipients)
    if sent:
        state.last_staff_digest_on = today
        state.save(update_fields=["last_staff_digest_on"])
    return sent


def process_loan_arrears(today=None) -> dict:
    today = today or timezone.localdate()
    stats = {
        "loans": 0,
        "first_notices": 0,
        "monthly_reminders": 0,
        "auto_debit_paid": 0,
        "auto_debit_failed": 0,
        "staff_digest": False,
        "charges": 0,
    }
    loans = MemberLoan.objects.filter(
        status__in=[MemberLoan.Status.ACTIVE, MemberLoan.Status.OVERDUE]
    ).select_related("user_profile", "user_profile__user")
    for loan in loans:
        stats["loans"] += 1
        before = q(loan.arrears_interest)
        sync_open_loan(loan, today=today)
        loan.refresh_from_db()
        if q(loan.arrears_interest) > before:
            stats["charges"] += 1
        notice = notify_member_overdue(loan, today=today)
        if notice == "first":
            stats["first_notices"] += 1
        elif notice == "monthly":
            stats["monthly_reminders"] += 1
        result = attempt_auto_debit(loan, today=today)
        if result == "paid":
            stats["auto_debit_paid"] += 1
        elif result == "failed":
            stats["auto_debit_failed"] += 1
    stats["staff_digest"] = send_staff_digest_if_due(today=today)
    return stats
