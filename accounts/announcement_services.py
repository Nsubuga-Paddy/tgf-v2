"""Publish staff announcements into member inboxes (and optional email)."""
from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import QuerySet
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from accounts.emails import get_site_base_url, log_email_for_testing
from accounts.models import MemberNotification, StaffAnnouncement

logger = logging.getLogger(__name__)
User = get_user_model()


def resolve_announcement_recipients(announcement: StaffAnnouncement) -> QuerySet:
    """Return distinct auth Users who should receive this announcement."""
    base = User.objects.filter(is_active=True).select_related("profile")

    if announcement.audience == StaffAnnouncement.Audience.ALL:
        return base.filter(profile__isnull=False).distinct()

    if announcement.audience == StaffAnnouncement.Audience.PROJECT:
        if not announcement.project_id:
            raise ValidationError(
                {"project": "Select a project when audience is “Members of a project”."}
            )
        return base.filter(profile__projects=announcement.project).distinct()

    if announcement.audience == StaffAnnouncement.Audience.SELECTED:
        profile_ids = list(
            announcement.selected_members.values_list("pk", flat=True)
        )
        if not profile_ids:
            raise ValidationError(
                {
                    "selected_members": (
                        "Select at least one member when audience is “Selected members”."
                    )
                }
            )
        return base.filter(profile__pk__in=profile_ids).distinct()

    raise ValidationError({"audience": "Unknown audience type."})


def _send_announcement_email(*, user, announcement: StaffAnnouncement) -> bool:
    email = (getattr(user, "email", None) or "").strip()
    if not email:
        return False

    site_url = get_site_base_url()
    login_url = f"{site_url}{reverse('login')}"
    profile = getattr(user, "profile", None)
    first_name = (user.first_name or "").strip() or user.get_username()
    subject = f"MCS notice: {announcement.title}"
    message = render_to_string(
        "core/staff_announcement_email.html",
        {
            "first_name": first_name,
            "title": announcement.title,
            "body": announcement.body,
            "account_number": getattr(profile, "account_number", None) if profile else None,
            "login_url": login_url,
            "site_url": site_url,
            "thanks_note": (
                "Thank you for saving and investing with Mushana Multipurpose "
                "Cooperative Society (MCS)."
            ),
        },
    )
    log_email_for_testing(
        to_email=email,
        subject=subject,
        body=message,
        context="staff_announcement",
    )
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        return True
    except Exception:
        logger.exception(
            "Failed staff announcement email to %s (%s).",
            user.get_username(),
            email,
        )
        return False


@transaction.atomic
def publish_staff_announcement(
    announcement: StaffAnnouncement,
    *,
    actor=None,
    force_republish: bool = False,
) -> dict:
    """
    Fan out inbox notifications (and optional emails) for a staff announcement.

    By default publishing twice is blocked. Pass force_republish=True only for
    intentional re-sends (creates duplicate inbox rows).
    """
    if (
        announcement.status == StaffAnnouncement.Status.PUBLISHED
        and not force_republish
    ):
        raise ValidationError("This announcement is already published.")

    recipients = list(resolve_announcement_recipients(announcement))
    if not recipients:
        raise ValidationError("No recipients matched this audience.")

    now = timezone.now()
    email_sent = 0
    email_failed = 0
    created = 0

    for user in recipients:
        notif = MemberNotification.objects.create(
            user=user,
            announcement=announcement,
            source=MemberNotification.Source.STAFF,
            title=announcement.title,
            body=announcement.body,
        )
        created += 1
        if announcement.send_email:
            ok = _send_announcement_email(user=user, announcement=announcement)
            if ok:
                email_sent += 1
                notif.email_sent = True
                notif.save(update_fields=["email_sent"])
            elif (getattr(user, "email", None) or "").strip():
                email_failed += 1

    announcement.status = StaffAnnouncement.Status.PUBLISHED
    announcement.published_at = now
    announcement.recipient_count = created
    announcement.email_sent_count = email_sent
    announcement.email_failed_count = email_failed
    if actor is not None and announcement.created_by_id is None:
        announcement.created_by = actor
    announcement.save(
        update_fields=[
            "status",
            "published_at",
            "recipient_count",
            "email_sent_count",
            "email_failed_count",
            "created_by",
            "updated_at",
        ]
    )

    return {
        "recipients": created,
        "email_sent": email_sent,
        "email_failed": email_failed,
    }


def serialize_notification(n: MemberNotification) -> dict:
    return {
        "id": n.pk,
        "title": n.title,
        "body": n.body,
        "source": n.source,
        "isRead": bool(n.is_read),
        "createdAt": n.created_at.isoformat() if n.created_at else "",
        "announcementId": n.announcement_id,
    }


def list_notifications_for_user(user, *, limit: int = 40) -> dict:
    qs = MemberNotification.objects.filter(user=user).order_by("-created_at", "-pk")
    unread = qs.filter(is_read=False).count()
    capped = max(1, min(int(limit or 40), 200))
    rows = [serialize_notification(n) for n in qs[:capped]]
    return {"unreadCount": unread, "notifications": rows, "totalCount": qs.count()}


def get_notification_for_user(user, notification_id: int) -> MemberNotification | None:
    return MemberNotification.objects.filter(user=user, pk=notification_id).first()


def mark_notification_read(user, notification_id: int) -> MemberNotification | None:
    n = MemberNotification.objects.filter(user=user, pk=notification_id).first()
    if not n:
        return None
    if not n.is_read:
        n.is_read = True
        n.read_at = timezone.now()
        n.save(update_fields=["is_read", "read_at"])
    return n


def mark_all_notifications_read(user) -> int:
    now = timezone.now()
    return MemberNotification.objects.filter(user=user, is_read=False).update(
        is_read=True,
        read_at=now,
    )
