"""Aggregates all data needed to render the member dashboard (home page).

Everything here is defensive: a failure in one project's data must never break
the whole dashboard. Amounts are Decimals; the template formats them.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from accounts.models import Project, ProjectAccessRequest
from main_account import services as ledger

ZERO = Decimal("0.00")

# Projects that have their own top-level treatment and should not appear as a
# normal "My Projects" card or in Discover.
SHAREHOLDING_NAME = "Cooperative Shareholding"


def _safe_reverse(url_name: str) -> str:
    if not url_name:
        return "#"
    try:
        return reverse(url_name)
    except NoReverseMatch:
        return "#"


def _week_of_year() -> int:
    """Jan-1 calendar week — same rule as savings_52_weeks member/group dashboards."""
    today = date.today()
    days_elapsed = (today - date(today.year, 1, 1)).days
    return min(days_elapsed // 7 + 1, 52)


def build_member_dashboard(user) -> dict:
    profile = getattr(user, "profile", None)
    ctx: dict = {
        "member_name": user.get_full_name() or user.get_username(),
        "first_name": user.first_name or user.get_username(),
        "initials": profile.initials if profile else user.get_username()[:2].upper(),
        "account_number": getattr(profile, "account_number", "") or "—",
        "is_verified": bool(getattr(profile, "is_verified", False)),
    }
    if profile is None:
        ctx.update(_empty_financials())
        return ctx

    # ---- Main account ----
    main_available = ledger.available_balance(profile)
    main_posted = ledger.posted_balance(profile)
    ctx["main_available"] = main_available
    ctx["main_posted"] = main_posted
    ctx["main_pending_withdrawal"] = ledger.pending_withdrawal_total(profile)

    # ---- Projects (My Projects) ----
    my_projects = _build_my_projects(user, profile)
    ctx["my_projects"] = my_projects
    total_invested = sum((p["invested"] for p in my_projects), ZERO)
    ctx["total_invested"] = total_invested
    ctx["my_projects_count"] = len(my_projects)

    # ---- Shareholding (top-level equity block) ----
    share_ctx = _build_shareholding(profile)
    ctx.update(share_ctx)

    # ---- Portfolio total ----
    share_value = share_ctx.get("coop_portfolio_value") or ZERO
    ctx["total_portfolio"] = main_posted + total_invested + share_value

    # ---- Pending requests summary ----
    pending_withdrawals = profile.main_account_withdrawals.filter(status="pending").count()
    pending_transfers = profile.project_transfer_requests.filter(status="pending").count()
    pending_access = profile.project_access_requests.filter(
        status=ProjectAccessRequest.STATUS_PENDING
    ).count()
    ctx["pending_count"] = pending_withdrawals + pending_transfers + pending_access
    ctx["pending_withheld"] = ctx["main_pending_withdrawal"]

    # ---- Discover ----
    ctx["discover_projects"] = _build_discover(profile)

    # ---- History (recent ledger) ----
    ctx["transactions"] = ledger.recent_transactions(profile, limit=50)

    return ctx


def _empty_financials() -> dict:
    return {
        "main_available": ZERO,
        "main_posted": ZERO,
        "main_pending_withdrawal": ZERO,
        "my_projects": [],
        "total_invested": ZERO,
        "my_projects_count": 0,
        "is_shareholder": False,
        "coop_portfolio_value": ZERO,
        "coop_summary": None,
        "total_portfolio": ZERO,
        "pending_count": 0,
        "pending_withheld": ZERO,
        "discover_projects": [],
        "transactions": [],
    }


def _card(name, icon, invested=ZERO, status_tag="Active", status_class="st-active",
          cycle_line="", url="#", stats=None, progress=None, transfer=None, card_id=None):
    return {
        "name": name,
        "icon": icon,
        "invested": invested,
        "status_tag": status_tag,
        "status_class": status_class,
        "cycle_line": cycle_line,
        "url": url,
        "stats": stats or [],
        "progress": progress,
        "transfer": transfer,  # {'label':..., 'suggested':Decimal} or None
        "card_id": card_id,
    }


def _build_my_projects(user, profile) -> list[dict]:
    cards: list[dict] = []
    names = set(profile.projects.values_list("name", flat=True))

    # ---- 52 Weeks Saving Challenge ----
    if "52 Weeks Saving Challenge" in names:
        try:
            saved = profile.get_current_year_amount_saved()
            available = profile.get_available_balance()
            try:
                from savings_52_weeks.interest_utils import calculate_unfixed_interest_ytd
                interest = calculate_unfixed_interest_ytd(profile) + sum(
                    inv.interest_gained_so_far for inv in profile.investments.all()
                )
            except Exception:
                interest = ZERO
            week = _week_of_year()
            cards.append(_card(
                "52 Weeks Saving Challenge", "fa-piggy-bank",
                invested=saved,
                cycle_line=f"Cycle {date.today().year} · Week {week} of 52",
                url=_safe_reverse("savings_52_weeks:member_dashboard"),
                stats=[
                    {"label": "Saved this year", "value": saved, "cls": "locked", "badge": "Locked"},
                    {"label": "Interest earned", "value": interest, "cls": "green", "badge": ""},
                    {"label": "Matured (transferable)", "value": available, "cls": "green", "badge": ""},
                ],
                progress={"pct": int(week / 52 * 100), "left": f"Week {week} / 52",
                          "right": f"Matures Dec {date.today().year}"},
                transfer=({"label": "52 Weeks Saving Challenge", "suggested": available}
                          if available > ZERO else None),
            ))
        except Exception:
            pass

    # ---- Commercial Goat Farming ----
    if "Commercial Goat Farming" in names:
        try:
            from goat_farming.models import UserFarmAccount, PackagePurchase
            from django.db.models import Sum
            invested = PackagePurchase.objects.filter(user=profile).aggregate(
                t=Sum("total_amount"))["t"] or ZERO
            goats = UserFarmAccount.objects.filter(user=profile, is_active=True).aggregate(
                t=Sum("current_goats"))["t"] or 0
            from datetime import timedelta
            cutoff = timezone.now() - timedelta(days=425)
            matured = PackagePurchase.objects.filter(
                user=profile, status="allocated", purchase_date__lte=cutoff
            ).exists()
            cards.append(_card(
                "Commercial Goat Farming", "fa-horse",
                invested=invested,
                status_tag="Matured" if matured else "Active",
                status_class="st-matured" if matured else "st-active",
                cycle_line="14-month cycle",
                url=_safe_reverse("goat_farming:dashboard"),
                stats=[
                    {"label": "Amount invested", "value": invested, "cls": "", "badge": ""},
                    {"label": "Current goats", "value": f"{goats} goats", "cls": "", "badge": "", "raw": True},
                ],
                transfer=({"label": "Commercial Goat Farming", "suggested": ZERO} if matured else None),
            ))
        except Exception:
            pass

    # ---- Generational Wealth Creation ----
    if "Generational Wealth Creation" in names:
        try:
            from gwc.services import portfolio_summary_for_user
            from gwc.models import GWCFixedDeposit
            port = portfolio_summary_for_user(user)
            principal = port.get("total_principal", ZERO)
            interest = port.get("total_accrued_interest", ZERO)
            next_mat = (
                GWCFixedDeposit.objects.filter(user=user, status=GWCFixedDeposit.Status.ACTIVE)
                .order_by("maturity_date").values_list("maturity_date", flat=True).first()
            )
            matured_count = GWCFixedDeposit.objects.filter(
                user=user, status=GWCFixedDeposit.Status.MATURED
            ).count() if hasattr(GWCFixedDeposit.Status, "MATURED") else 0
            cards.append(_card(
                "Generational Wealth Creation", "fa-hand-holding-heart",
                invested=principal,
                status_tag="Matured" if matured_count else "Active",
                status_class="st-matured" if matured_count else "st-active",
                cycle_line="Fixed deposits",
                url=_safe_reverse("gwc:gwc"),
                stats=[
                    {"label": "Total deposited", "value": principal, "cls": "", "badge": ""},
                    {"label": "Accrued interest", "value": interest, "cls": "green", "badge": ""},
                    {"label": "Nearest maturity",
                     "value": next_mat.strftime("%d %b %Y") if next_mat else "—",
                     "cls": "", "badge": "", "raw": True},
                ],
                transfer=({"label": "Generational Wealth Creation", "suggested": ZERO}
                          if matured_count else None),
            ))
        except Exception:
            pass

    # ---- Real Estate Projects (per allowed project) ----
    try:
        from realestate_projects.models import RealEstateProject
        for project in RealEstateProject.objects.filter(allowed_members=user).distinct():
            bal = _rep_balances(user, project)
            cards.append(_card(
                f"Real Estate · {project.name}", "fa-city",
                invested=bal["gross"],
                cycle_line=getattr(project, "location", "") or "Real estate",
                url=_safe_reverse("realestate_projects:rep"),
                card_id=f"rep-{project.pk}",
                stats=[
                    {"label": "Total contributed", "value": bal["gross"], "cls": "", "badge": ""},
                    {"label": "Withheld", "value": bal["withheld"], "cls": "", "badge": ""},
                    {"label": "Available (transferable)", "value": bal["available"], "cls": "green", "badge": ""},
                ],
                transfer=({"label": f"Real Estate · {project.name}", "suggested": bal["available"]}
                          if bal["available"] > ZERO else None),
            ))
    except Exception:
        pass

    return cards


def _rep_balances(user, project) -> dict:
    """Best-effort real estate balances (mirrors ProfileView logic)."""
    out = {"gross": ZERO, "withheld": ZERO, "deducted": ZERO, "available": ZERO}
    try:
        from django.db.models import Sum
        from realestate_projects.models import (
            RealEstateProjectActionRequest,
            RealEstateProjectTransaction,
        )
        gross = ZERO
        for txn in RealEstateProjectTransaction.objects.filter(user=user, project=project):
            if txn.type in (
                RealEstateProjectTransaction.TYPE_PAYMENT,
                RealEstateProjectTransaction.TYPE_ADJUSTMENT,
            ):
                gross += txn.amount
            elif txn.type == RealEstateProjectTransaction.TYPE_REFUND:
                gross -= txn.amount
        withheld = RealEstateProjectActionRequest.objects.filter(
            user=user, project=project, status=RealEstateProjectActionRequest.STATUS_PENDING
        ).aggregate(t=Sum("amount"))["t"] or ZERO
        deducted = RealEstateProjectActionRequest.objects.filter(
            user=user, project=project,
            status__in=[
                RealEstateProjectActionRequest.STATUS_APPROVED,
                RealEstateProjectActionRequest.STATUS_PROCESSED,
            ],
        ).aggregate(t=Sum("amount"))["t"] or ZERO
        gross = gross if gross > ZERO else ZERO
        out.update({
            "gross": gross,
            "withheld": withheld,
            "deducted": deducted,
            "available": max(ZERO, gross - withheld - deducted),
        })
    except Exception:
        pass
    return out


def _build_shareholding(profile) -> dict:
    try:
        from cooperative_shareholding.services import (
            build_shareholding_summary,
            cooperative_display_state,
        )
    except Exception:
        return {"is_shareholder": False, "coop_portfolio_value": ZERO, "coop_summary": None}

    holding = None
    try:
        holding = profile.user.cooperative_shareholding
    except Exception:
        holding = None

    state = cooperative_display_state(profile, holding)
    if holding is not None and state == "full":
        try:
            summary = build_shareholding_summary(holding)
            return {
                "is_shareholder": True,
                "coop_summary": summary,
                "coop_portfolio_value": summary.get("portfolio_value") or ZERO,
                "coop_year_joined": summary.get("year_joined"),
                "coop_election_open": holding.dividend_election_open,
            }
        except Exception:
            pass
    return {"is_shareholder": False, "coop_portfolio_value": ZERO, "coop_summary": None}


def _build_discover(profile) -> list[dict]:
    granted_ids = set(profile.projects.values_list("pk", flat=True))
    pending_ids = set(
        profile.project_access_requests.filter(
            status=ProjectAccessRequest.STATUS_PENDING
        ).values_list("project_id", flat=True)
    )
    rejected_ids = set(
        profile.project_access_requests.filter(
            status=ProjectAccessRequest.STATUS_REJECTED
        ).values_list("project_id", flat=True)
    )

    out = []
    qs = Project.objects.filter(is_public=True).exclude(name=SHAREHOLDING_NAME)
    for p in qs:
        if p.pk in granted_ids:
            continue  # already a member; shown under My Projects
        if p.status == Project.Status.COMING_SOON:
            state = "coming_soon"
        elif p.status == Project.Status.CLOSED:
            state = "closed"
        elif p.pk in pending_ids:
            state = "pending"
        elif not p.accepts_requests:
            state = "closed"
        else:
            state = "request"
        out.append({
            "id": p.pk,
            "name": p.name,
            "icon": p.icon or "fa-layer-group",
            "summary": p.summary or p.description or "",
            "rate": p.rate_display,
            "min_entry": p.min_entry_display,
            "cycle": p.cycle_display,
            "status": p.status,
            "state": state,
            "was_rejected": p.pk in rejected_ids,
        })
    return out
