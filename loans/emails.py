from __future__ import annotations

import logging
from decimal import Decimal

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse

from accounts.emails import get_site_base_url, log_email_for_testing

logger = logging.getLogger(__name__)


def _money(amount) -> str:
    return f"{Decimal(amount or 0):,.0f}"


def send_loan_disbursement_email(loan) -> bool:
    """
    Email the member the full terms of a newly disbursed loan.
    Returns True if sent, False on skip/failure.
    """
    profile = loan.user_profile
    user = profile.user
    email = (getattr(user, "email", None) or "").strip()
    if not email:
        logger.warning(
            "Skipped loan disbursement email for user %s: no email on file.",
            user.get_username(),
        )
        return False

    site_url = get_site_base_url()
    login_url = f"{site_url}{reverse('login')}"
    loan_url = f"{site_url}/loans/facility/{loan.pk}"
    principal = Decimal(loan.principal or 0)
    outstanding = Decimal(loan.outstanding or 0)
    total_interest = outstanding - principal
    if total_interest < 0:
        total_interest = Decimal("0")

    subject = f"Your MCS loan {loan.reference} has been disbursed"
    message = render_to_string(
        "core/loan_disbursement_email.html",
        {
            "user": user,
            "login_url": login_url,
            "loan_url": loan_url,
            "site_url": site_url,
            "account_number": getattr(profile, "account_number", None),
            "loan_reference": loan.reference,
            "purpose_label": loan.get_purpose_display(),
            "amount_display": _money(principal),
            "insurance_fee_display": _money(loan.insurance_fee),
            "processing_fee_display": _money(loan.processing_fee),
            "total_deductions_display": _money(loan.total_deductions),
            "net_disbursed_display": _money(loan.net_disbursed_amount or principal),
            "term_months": loan.term_months,
            "rate_display": loan.rate_display,
            "total_interest_display": _money(total_interest),
            "total_repayable_display": _money(outstanding),
            "installment_display": _money(loan.installment_amount),
            "first_due_date": loan.first_due_date.strftime("%d %b %Y") if loan.first_due_date else "—",
            "disbursed_date": loan.disbursed_date.strftime("%d %b %Y") if loan.disbursed_date else "—",
        },
    )

    log_email_for_testing(
        to_email=email,
        subject=subject,
        body=message,
        context="loan_disbursement",
    )

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        logger.info(
            "Sent loan disbursement email for %s to %s (%s).",
            loan.reference,
            user.get_username(),
            email,
        )
        return True
    except Exception:
        logger.exception(
            "Failed to send loan disbursement email for %s to %s (%s).",
            loan.reference,
            user.get_username(),
            email,
        )
        return False
