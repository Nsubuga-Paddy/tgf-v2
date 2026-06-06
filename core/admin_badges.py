"""
Admin sidebar badges for pending items awaiting administrator action.
"""
from __future__ import annotations

from typing import Callable


def _badge_label(label: str, count: int) -> str:
    base = str(label).split(" (")[0]
    if count <= 0:
        return base
    return f"{base} ({count})"


def pending_user_verification_count() -> int:
    from accounts.models import UserProfile

    return UserProfile.objects.filter(is_verified=False).count()


def pending_project_access_request_count() -> int:
    from accounts.models import ProjectAccessRequest

    return ProjectAccessRequest.objects.filter(
        status=ProjectAccessRequest.STATUS_PENDING,
    ).count()


def pending_withdrawal_request_count() -> int:
    from accounts.models import WithdrawalRequest

    return WithdrawalRequest.objects.filter(status="pending").count()


def pending_dividend_request_count() -> int:
    from cooperative_shareholding.models import DividendChoiceRequest

    return DividendChoiceRequest.objects.filter(
        status=DividendChoiceRequest.Status.PENDING,
    ).count()


def pending_cgf_action_request_count() -> int:
    from goat_farming.models import CGFActionRequest

    return CGFActionRequest.objects.filter(status="pending").count()


def pending_realestate_action_request_count() -> int:
    from realestate_projects.models import RealEstateProjectActionRequest

    return RealEstateProjectActionRequest.objects.filter(
        status=RealEstateProjectActionRequest.STATUS_PENDING,
    ).count()


# (app_label, model object_name) → pending count callable
ADMIN_PENDING_BADGE_COUNTERS: dict[tuple[str, str], Callable[[], int]] = {
    ("auth", "User"): pending_user_verification_count,
    ("accounts", "ProjectAccessRequest"): pending_project_access_request_count,
    ("accounts", "WithdrawalRequest"): pending_withdrawal_request_count,
    ("cooperative_shareholding", "DividendChoiceRequest"): pending_dividend_request_count,
    ("goat_farming", "CGFActionRequest"): pending_cgf_action_request_count,
    (
        "realestate_projects",
        "RealEstateProjectActionRequest",
    ): pending_realestate_action_request_count,
}


def apply_pending_badges_to_app_list(app_list: list) -> list:
    for app in app_list:
        app_label = app.get("app_label", "")
        for model in app.get("models", []):
            key = (app_label, model.get("object_name", ""))
            counter = ADMIN_PENDING_BADGE_COUNTERS.get(key)
            if not counter:
                continue
            try:
                count = counter()
            except Exception:
                continue
            model["name"] = _badge_label(model.get("name", ""), count)
    return app_list


def patch_admin_pending_badges() -> None:
    from django.contrib.admin.sites import AdminSite

    if getattr(AdminSite, "_mcs_admin_pending_badges_patched", False):
        return

    original_get_app_list = AdminSite.get_app_list

    def get_app_list(self, request, app_label=None):
        app_list = original_get_app_list(self, request, app_label)
        return apply_pending_badges_to_app_list(app_list)

    AdminSite.get_app_list = get_app_list
    AdminSite._mcs_admin_pending_badges_patched = True
