from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse

logger = logging.getLogger(__name__)


def get_site_base_url() -> str:
    """Public site URL for links in outbound email (no trailing slash)."""
    configured = (getattr(settings, "SITE_URL", None) or "").strip().rstrip("/")
    if configured:
        return configured
    hosts = [h for h in getattr(settings, "ALLOWED_HOSTS", []) if h and h != "*"]
    if hosts:
        host = hosts[0]
        if host in ("localhost", "127.0.0.1"):
            return f"http://{host}:8000"
        return f"https://{host}"
    return "http://127.0.0.1:8000"


def send_account_verified_email(user) -> bool:
    """
    Notify a member that their account has been verified.
    Returns True if the message was sent (or queued by backend), False on skip/failure.
    """
    email = (getattr(user, "email", None) or "").strip()
    if not email:
        logger.warning(
            "Skipped verification email for user %s: no email on file.",
            user.get_username(),
        )
        return False

    site_url = get_site_base_url()
    login_url = f"{site_url}{reverse('login')}"
    profile = getattr(user, "profile", None)
    account_number = getattr(profile, "account_number", None) if profile else None

    subject = "Your MCS account has been verified"
    message = render_to_string(
        "core/account_verified_email.html",
        {
            "user": user,
            "login_url": login_url,
            "site_url": site_url,
            "account_number": account_number,
        },
    )

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        logger.info("Sent verification email to %s (%s).", user.get_username(), email)
        return True
    except Exception:
        logger.exception(
            "Failed to send verification email to %s (%s).",
            user.get_username(),
            email,
        )
        return False
