from __future__ import annotations

from decimal import Decimal

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from main_account import services as main_ledger

from .models import LoanApplication, LoanInstallment, LoanRepayment, MemberLoan
from .services import (
    PAYMENT_DETAILS,
    calculate_eligibility,
    create_application,
    loan_disbursement_breakdown,
    purpose_label,
    repayment_source_label,
    repay_from_main_account,
)


def money(value) -> int:
    if value is None:
        return 0
    if isinstance(value, Decimal):
        return int(value.quantize(Decimal("1")))
    return int(value)


def date_label(value) -> str:
    if not value:
        return ""
    return value.strftime("%d %b %Y")


def datetime_iso(value) -> str:
    if not value:
        return ""
    return timezone.localtime(value).isoformat()


def rate_display(value) -> str:
    pct = (Decimal(value or 0) * Decimal("100")).quantize(Decimal("0.01"))
    return f"{pct.normalize()}% per month on principal"


def serialize_fee_breakdown(amount) -> dict:
    breakdown = loan_disbursement_breakdown(amount)
    return {
        "insuranceFee": money(breakdown["insurance_fee"]),
        "processingFee": money(breakdown["processing_fee"]),
        "totalDeductions": money(breakdown["total_deductions"]),
        "netDisbursedAmount": money(breakdown["net_disbursed_amount"]),
    }


def serialize_application(app: LoanApplication) -> dict:
    timeline = [
        {
            "status": "submitted",
            "at": datetime_iso(app.submitted_at),
            "note": "Application received online.",
        }
    ]
    if app.status in {
        LoanApplication.Status.UNDER_REVIEW,
        LoanApplication.Status.APPROVED,
        LoanApplication.Status.DISBURSED,
        LoanApplication.Status.REJECTED,
    }:
        timeline.append(
            {
                "status": "under_review",
                "at": datetime_iso(app.reviewed_at or app.updated_at),
                "note": "Assigned to the credit committee.",
            }
        )
    if app.status == LoanApplication.Status.REJECTED:
        timeline.append(
            {
                "status": "rejected",
                "at": datetime_iso(app.reviewed_at or app.updated_at),
                "note": app.rejection_reason or "Application was not approved.",
            }
        )
    elif app.status in {LoanApplication.Status.APPROVED, LoanApplication.Status.DISBURSED}:
        timeline.append(
            {
                "status": "approved",
                "at": datetime_iso(app.reviewed_at or app.updated_at),
                "note": app.committee_note or "Application approved.",
            }
        )
    if app.status == LoanApplication.Status.DISBURSED:
        timeline.append(
            {
                "status": "disbursed",
                "at": datetime_iso(app.disbursed_at),
                "note": "Net funds were credited to your Main Account after upfront deductions.",
            }
        )
    return {
        "id": str(app.pk),
        "reference": app.reference,
        "purpose": app.purpose,
        "purposeLabel": purpose_label(app.purpose),
        "amount": money(app.amount_requested),
        "approvedAmount": money(app.approved_amount),
        "fees": serialize_fee_breakdown(app.approved_amount or app.amount_requested),
        "termMonths": app.approved_term_months or app.term_months,
        "status": app.status,
        "statusDisplay": app.get_status_display(),
        "submittedAt": datetime_iso(app.submitted_at),
        "notes": app.notes or "",
        "repaymentSource": app.repayment_source,
        "repaymentSourceLabel": repayment_source_label(app.repayment_source),
        "timeline": timeline,
        "committeeNote": app.committee_note or app.rejection_reason or "",
    }


def serialize_installment(row: LoanInstallment) -> dict:
    return {
        "installment": row.installment_number,
        "dueDate": date_label(row.due_date),
        "principal": money(row.principal_amount),
        "interest": money(row.interest_amount),
        "total": money(row.total_amount),
        "balanceAfter": money(row.balance_after),
        "status": row.status,
    }


def serialize_repayment(payment: LoanRepayment) -> dict:
    reference = payment.reference
    if payment.external_reference:
        reference = f"{reference} - {payment.external_reference}"
    return {
        "id": str(payment.pk),
        "date": date_label(timezone.localdate(payment.posted_at)),
        "amount": money(payment.amount),
        "outstandingAfter": money(payment.outstanding_after),
        "method": payment.get_method_display(),
        "reference": reference,
        "status": "completed",
    }


def serialize_loan(loan: MemberLoan) -> dict:
    schedule = list(loan.installments.all())
    payments = list(loan.repayments.all())
    next_due = next((row for row in schedule if row.status == LoanInstallment.Status.DUE), None)
    return {
        "id": str(loan.pk),
        "reference": loan.reference,
        "purpose": loan.purpose,
        "purposeLabel": purpose_label(loan.purpose),
        "status": loan.status,
        "principal": money(loan.principal),
        "insuranceFee": money(loan.insurance_fee),
        "processingFee": money(loan.processing_fee),
        "totalDeductions": money(loan.total_deductions),
        "netDisbursedAmount": money(loan.net_disbursed_amount or loan.principal),
        "outstanding": money(loan.outstanding),
        "rateDisplay": rate_display(loan.monthly_interest_rate),
        "monthlyRate": float(loan.monthly_interest_rate),
        "termMonths": loan.term_months,
        "disbursedDate": date_label(loan.disbursed_date),
        "nextDueDate": date_label(next_due.due_date) if next_due else "",
        "nextDueAmount": money(next_due.total_amount) if next_due else 0,
        "installmentAmount": money(loan.installment_amount),
        "paidInstallments": loan.paid_installments,
        "schedule": [serialize_installment(row) for row in schedule],
        "payments": [serialize_repayment(payment) for payment in payments],
    }


def serialize_closed_loan(loan: MemberLoan) -> dict:
    total_repaid = sum((payment.amount for payment in loan.repayments.all()), Decimal("0.00"))
    return {
        "id": str(loan.pk),
        "reference": loan.reference,
        "purpose": loan.purpose,
        "purposeLabel": purpose_label(loan.purpose),
        "closedDate": date_label(loan.closed_date),
        "principal": money(loan.principal),
        "totalRepaid": money(total_repaid),
    }


def repayment_methods() -> list[dict]:
    return [
        {
            "id": "main_account",
            "label": "Main Account",
            "shortLabel": "Main Account",
            "description": "Transfer from your MCS Main Account balance.",
            "memberInitiated": True,
            "cta": "Repay now",
        },
        {
            "id": "bank_transfer",
            "label": "Bank transfer",
            "shortLabel": "Bank transfer",
            "description": (
                "Transfer to the MCS bank account below. After payment, share your bank "
                "receipt with MCS staff. They will verify the deposit and update your loan balance."
            ),
            "memberInitiated": False,
        },
    ]


def hub_payload(profile) -> dict:
    active = (
        MemberLoan.objects.filter(
            user_profile=profile,
            status__in=[MemberLoan.Status.ACTIVE, MemberLoan.Status.OVERDUE],
        )
        .prefetch_related("installments", "repayments")
        .order_by("-created_at")
    )
    closed = (
        MemberLoan.objects.filter(user_profile=profile, status=MemberLoan.Status.CLOSED)
        .prefetch_related("repayments")
        .order_by("-closed_date", "-created_at")
    )
    applications = (
        LoanApplication.objects.filter(user_profile=profile)
        .select_related("decided_by")
        .order_by("-created_at")
    )
    return {
        "eligibility": calculate_eligibility(profile),
        "applications": [serialize_application(app) for app in applications],
        "activeLoans": [serialize_loan(loan) for loan in active],
        "closedLoans": [serialize_closed_loan(loan) for loan in closed],
        "repaymentMethods": repayment_methods(),
        "paymentDetails": PAYMENT_DETAILS,
        "mainAccount": {
            "available": money(main_ledger.available_balance(profile)),
            "posted": money(main_ledger.posted_balance(profile)),
            "pendingWithdrawal": money(main_ledger.pending_withdrawal_total(profile)),
        },
    }


class LoansHubAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(hub_payload(request.user.profile))


class LoanEligibilityAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        return Response({"eligibility": calculate_eligibility(request.user.profile)})


class LoanApplyAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        data = request.data or {}
        try:
            app = create_application(
                request.user.profile,
                purpose=(data.get("purpose") or "").strip(),
                amount=Decimal(str(data.get("amount") or "0").replace(",", "")),
                term_months=int(data.get("termMonths") or data.get("term_months") or 0),
                repayment_source=(data.get("repaymentSource") or data.get("repayment_source") or "").strip(),
                notes=(data.get("notes") or "").strip(),
            )
        except (ValueError, ArithmeticError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"ok": True, "application": serialize_application(app), **hub_payload(request.user.profile)},
            status=status.HTTP_201_CREATED,
        )


class LoanApplicationDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, application_id: int):
        app = get_object_or_404(LoanApplication, pk=application_id, user_profile=request.user.profile)
        return Response({"application": serialize_application(app)})


class LoanFacilityDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, loan_id: int):
        loan = get_object_or_404(
            MemberLoan.objects.prefetch_related("installments", "repayments"),
            pk=loan_id,
            user_profile=request.user.profile,
        )
        return Response({"loan": serialize_loan(loan)})


class LoanRepayFromMainAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, loan_id: int):
        try:
            data = request.data or {}
            amount = Decimal(str(data.get("amount") or "0").replace(",", ""))
            notes = (data.get("notes") or "").strip()
            repayment = repay_from_main_account(
                request.user.profile,
                loan_id,
                amount,
                notes=notes,
            )
        except (ValueError, MemberLoan.DoesNotExist, ArithmeticError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "ok": True,
                "message": "Repayment posted from Main Account. Your loan balance has been updated.",
                "repayment": serialize_repayment(repayment),
                **hub_payload(request.user.profile),
            }
        )
