"""
Member milestone emails: birthday celebrations and matured / redeemable digests.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import date
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import IntegrityError
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from accounts.emails import get_site_base_url, log_email_for_testing
from accounts.models import MemberEmailNotification, UserProfile

logger = logging.getLogger(__name__)
User = get_user_model()
ZERO = Decimal("0.00")


def _fmt_ugx(amount) -> str:
    try:
        value = Decimal(str(amount or 0))
    except Exception:
        value = ZERO
    return f"UGX {value:,.0f}"


def _member_first_name(user) -> str:
    first = (getattr(user, "first_name", None) or "").strip()
    if first:
        return first
    return user.get_username()


def _login_url() -> str:
    return f"{get_site_base_url()}{reverse('login')}"


def _already_sent(user, event_type: str, event_key: str) -> bool:
    return MemberEmailNotification.objects.filter(
        user=user,
        event_type=event_type,
        event_key=event_key,
    ).exists()


def _record_sent(user, event_type: str, event_key: str, subject: str, meta: dict | None = None) -> bool:
    try:
        MemberEmailNotification.objects.create(
            user=user,
            event_type=event_type,
            event_key=event_key,
            subject=subject,
            meta=meta or {},
            sent_at=timezone.now(),
        )
        return True
    except IntegrityError:
        return False


def _send_plain_email(*, user, subject: str, template: str, context: dict) -> bool:
    email = (getattr(user, "email", None) or "").strip()
    if not email:
        logger.warning(
            "Skipped milestone email for user %s: no email on file.",
            user.get_username(),
        )
        return False
    message = render_to_string(template, context)
    log_email_for_testing(
        to_email=email,
        subject=subject,
        body=message,
        context="milestone",
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
            "Sent milestone email (%s) to %s (%s).",
            subject,
            user.get_username(),
            email,
        )
        return True
    except Exception:
        logger.exception(
            "Failed milestone email for %s (%s).",
            user.get_username(),
            email,
        )
        return False


def collect_maturity_items(profile: UserProfile) -> list[dict[str, Any]]:
    """
    Build actionable maturity / redeemable items for one member.
    Reuses the same business rules as the home Matured projects section.
    """
    items: list[dict[str, Any]] = []
    user = profile.user

    # CGF matured unsettled cycles
    try:
        from goat_farming.services import matured_transfer_preview

        preview = matured_transfer_preview(profile)
        if preview.get("can_transfer"):
            items.append(
                {
                    "code": "cgf",
                    "title": "Commercial Goat Farming",
                    "amount": preview.get("available") or ZERO,
                    "amount_label": _fmt_ugx(preview.get("available")),
                    "detail": (
                        f"{preview.get('matured_count', 0)} matured cycle(s) ready · "
                        f"{preview.get('matured_goats', 0)} goats + "
                        f"{preview.get('matured_kids', 0)} kids"
                    ),
                    "actions": [
                        "Open Matured projects on your MCS home page",
                        "Transfer matured CGF value to your Main Account",
                        "Request a bank withdrawal from Main Account when ready",
                    ],
                    "fingerprint": f"cgf:{preview.get('matured_count')}:{preview.get('available')}",
                }
            )
    except Exception:
        logger.exception("CGF maturity collect failed for profile %s", profile.pk)

    # 52WSC matured cycle awaiting action
    try:
        from savings_52_weeks.cycle_service import sync_member_cycles
        from savings_52_weeks.models import SavingsCycle

        sync_member_cycles(profile)
        cycle = (
            SavingsCycle.objects.filter(
                user_profile=profile,
                status__in=[
                    SavingsCycle.STATUS_AWAITING_DECISION,
                    SavingsCycle.STATUS_POT_AVAILABLE,
                ],
            )
            .order_by("-cycle_number")
            .first()
        )
        if cycle:
            principal = cycle.amount_saved or ZERO
            earnings = cycle.interest_earned or ZERO
            bf = cycle.balance_brought_forward or ZERO
            available = principal + earnings + bf
            items.append(
                {
                    "code": "52wsc",
                    "title": "52 Weeks Saving Challenge",
                    "amount": available,
                    "amount_label": _fmt_ugx(available),
                    "detail": f"{cycle.label} · status {cycle.get_status_display()}",
                    "actions": [
                        "Open your 52WSC dashboard",
                        "Start a new cycle with balance brought forward, or",
                        "Transfer your matured pot to Main Account",
                    ],
                    "fingerprint": f"52wsc:{cycle.pk}:{cycle.status}:{available}",
                }
            )
    except Exception:
        logger.exception("52WSC maturity collect failed for profile %s", profile.pk)

    # GWC redeemable monthly interest
    try:
        from gwc.services import redeemable_interest_summary_for_user

        gwc = redeemable_interest_summary_for_user(user)
        if gwc.get("has_redeemable"):
            items.append(
                {
                    "code": "gwc",
                    "title": "Generational Wealth Creation",
                    "amount": gwc.get("total_redeemable") or ZERO,
                    "amount_label": _fmt_ugx(gwc.get("total_redeemable")),
                    "detail": (
                        f"{gwc.get('deposit_count', 0)} deposit(s) with redeemable "
                        "monthly interest"
                    ),
                    "actions": [
                        "Open Matured projects or your GWC page",
                        "Redeem full or partial interest to Main Account",
                        "Withdraw from Main Account when you need the funds",
                    ],
                    "fingerprint": (
                        f"gwc:{gwc.get('primary_deposit_id')}:"
                        f"{gwc.get('total_redeemable')}"
                    ),
                }
            )
    except Exception:
        logger.exception("GWC redeemable collect failed for profile %s", profile.pk)

    return items


def maturity_digest_key(items: list[dict[str, Any]]) -> str:
    raw = "|".join(sorted(str(i.get("fingerprint") or "") for i in items))
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    return f"digest:{digest}"


def send_maturity_digest_email(user, items: list[dict[str, Any]], *, dry_run: bool = False) -> str:
    """
    Send matured / redeemable digest. Returns status: sent|skipped|dry_run|failed|no_email.
    """
    if not items:
        return "skipped"
    email = (getattr(user, "email", None) or "").strip()
    if not email:
        return "no_email"

    event_key = maturity_digest_key(items)
    if _already_sent(user, MemberEmailNotification.EventType.MATURITY_DIGEST, event_key):
        return "skipped"

    profile = getattr(user, "profile", None)
    subject = "MCS update: funds ready on your matured / redeemable projects"
    context = {
        "first_name": _member_first_name(user),
        "account_number": getattr(profile, "account_number", None) if profile else None,
        "items": items,
        "login_url": _login_url(),
        "site_url": get_site_base_url(),
        "thanks_note": (
            "Thank you for saving and investing with Mushana Multipurpose "
            "Cooperative Society (MCS)."
        ),
    }

    if dry_run:
        return "dry_run"

    if not _send_plain_email(
        user=user,
        subject=subject,
        template="core/maturity_digest_email.html",
        context=context,
    ):
        return "failed"

    if not _record_sent(
        user,
        MemberEmailNotification.EventType.MATURITY_DIGEST,
        event_key,
        subject,
        meta={
            "codes": [i.get("code") for i in items],
            "amounts": [str(i.get("amount") or 0) for i in items],
        },
    ):
        return "skipped"
    return "sent"


def profiles_with_birthday_today(as_of: date | None = None):
    as_of = as_of or timezone.localdate()
    return (
        UserProfile.objects.filter(
            birthdate__month=as_of.month,
            birthdate__day=as_of.day,
        )
        .exclude(birthdate__isnull=True)
        .select_related("user")
    )


def send_birthday_email(user, *, as_of: date | None = None, dry_run: bool = False) -> str:
    as_of = as_of or timezone.localdate()
    email = (getattr(user, "email", None) or "").strip()
    if not email:
        return "no_email"

    event_key = f"birthday:{as_of.year}"
    if _already_sent(user, MemberEmailNotification.EventType.BIRTHDAY, event_key):
        return "skipped"

    profile = getattr(user, "profile", None)
    subject = "Happy Birthday from MCS!"
    context = {
        "first_name": _member_first_name(user),
        "account_number": getattr(profile, "account_number", None) if profile else None,
        "login_url": _login_url(),
        "site_url": get_site_base_url(),
        "thanks_note": (
            "Thank you for saving and investing with Mushana Multipurpose "
            "Cooperative Society (MCS). We celebrate you today!"
        ),
    }

    if dry_run:
        return "dry_run"

    if not _send_plain_email(
        user=user,
        subject=subject,
        template="core/birthday_email.html",
        context=context,
    ):
        return "failed"

    if not _record_sent(
        user,
        MemberEmailNotification.EventType.BIRTHDAY,
        event_key,
        subject,
        meta={"year": as_of.year},
    ):
        return "skipped"
    return "sent"


def run_member_milestone_notifications(
    *,
    as_of: date | None = None,
    dry_run: bool = False,
    birthdays: bool = True,
    maturity: bool = True,
) -> dict[str, int]:
    """
    Scan members and send birthday + maturity/redeemable emails.
    Dedupes via MemberEmailNotification.
    """
    as_of = as_of or timezone.localdate()
    stats = {
        "birthday_sent": 0,
        "birthday_skipped": 0,
        "birthday_failed": 0,
        "birthday_no_email": 0,
        "maturity_sent": 0,
        "maturity_skipped": 0,
        "maturity_failed": 0,
        "maturity_no_email": 0,
        "maturity_candidates": 0,
    }

    if birthdays:
        for profile in profiles_with_birthday_today(as_of):
            status = send_birthday_email(profile.user, as_of=as_of, dry_run=dry_run)
            if status == "sent" or status == "dry_run":
                stats["birthday_sent"] += 1
            elif status == "no_email":
                stats["birthday_no_email"] += 1
            elif status == "failed":
                stats["birthday_failed"] += 1
            else:
                stats["birthday_skipped"] += 1

    if maturity:
        # Members who likely have project activity: any project membership.
        profiles = (
            UserProfile.objects.filter(projects__isnull=False)
            .select_related("user")
            .distinct()
        )
        for profile in profiles:
            items = collect_maturity_items(profile)
            if not items:
                continue
            stats["maturity_candidates"] += 1
            status = send_maturity_digest_email(profile.user, items, dry_run=dry_run)
            if status == "sent" or status == "dry_run":
                stats["maturity_sent"] += 1
            elif status == "no_email":
                stats["maturity_no_email"] += 1
            elif status == "failed":
                stats["maturity_failed"] += 1
            else:
                stats["maturity_skipped"] += 1

    return stats
