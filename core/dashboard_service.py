"""Aggregates all data needed to render the member dashboard (home page).

Everything here is defensive: a failure in one project's data must never break
the whole dashboard. Amounts are Decimals; the template formats them.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db.models import Sum
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
    pending_rep = 0
    pending_rep_amount = ZERO
    try:
        from realestate_projects.models import RealEstateProjectActionRequest

        rep_pending_qs = RealEstateProjectActionRequest.objects.filter(
            user=user,
            status=RealEstateProjectActionRequest.STATUS_PENDING,
        )
        pending_rep = rep_pending_qs.count()
        pending_rep_amount = rep_pending_qs.aggregate(t=Sum("amount"))["t"] or ZERO
    except Exception:
        pending_rep = 0
        pending_rep_amount = ZERO

    ctx["pending_count"] = (
        pending_withdrawals + pending_transfers + pending_access + pending_rep
    )
    ctx["pending_withheld"] = ctx["main_pending_withdrawal"] + pending_rep_amount
    ctx["pending_rep_count"] = pending_rep
    ctx["pending_rep_amount"] = pending_rep_amount

    # ---- Discover ----
    ctx["discover_projects"] = _build_discover(profile)

    # ---- Matured projects (aggregated cards for the home dashboard) ----
    ctx["matured_projects"] = _build_matured_projects(profile, ctx.get("my_projects") or [])

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
        "pending_rep_count": 0,
        "pending_rep_amount": ZERO,
        "discover_projects": [],
        "matured_projects": [],
        "transactions": [],
    }


def _format_coop_date(dt) -> str:
    if not dt:
        return ""
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_default_timezone())
    return timezone.localtime(dt, timezone.get_default_timezone()).strftime("%d %b %Y")


def _cgf_maturity_summary(profile) -> dict:
    """Summarise matured vs still-active CGF package cycles for one member."""
    from goat_farming.models import CGF_CASHOUT_PRICE_PER_GOAT, PackagePurchase, UserFarmAccount
    from goat_farming.services import (
        eligible_cycle_queryset,
        is_purchase_matured,
        maturity_datetime,
        member_cycle_progress,
        purchase_cycle_goats,
        purchase_cycle_kids,
    )

    now = timezone.now()
    # Settled cycles were already transferred to Main Account — exclude them.
    # Eligible = Fully Paid or Goats Allocated (purchase_date drives the 425-day clock).
    cycles = list(eligible_cycle_queryset(profile, unsettled_only=True))
    matured = [p for p in cycles if is_purchase_matured(p, now=now)]
    active = [p for p in cycles if not is_purchase_matured(p, now=now)]

    matured_goats = sum(purchase_cycle_goats(p) for p in matured)
    matured_kids = sum(purchase_cycle_kids(p) for p in matured)
    principal = sum((p.amount_paid or p.total_amount or ZERO) for p in matured)
    if not isinstance(principal, Decimal):
        principal = Decimal(str(principal or 0))
    available = Decimal(matured_goats + matured_kids) * CGF_CASHOUT_PRICE_PER_GOAT
    earnings = available - principal
    if earnings < ZERO:
        earnings = ZERO

    earliest = None
    if matured:
        dates = [p.purchase_date for p in matured if p.purchase_date]
        if dates:
            earliest = maturity_datetime(min(dates))

    progress = member_cycle_progress(profile)

    total_goats = (
        UserFarmAccount.objects.filter(user=profile, is_active=True).aggregate(
            t=Sum("current_goats")
        )["t"]
        or 0
    )
    invested = PackagePurchase.objects.filter(user=profile).aggregate(t=Sum("total_amount"))[
        "t"
    ] or ZERO

    return {
        "matured_count": len(matured),
        "active_count": len(active),
        "has_matured": bool(matured),
        "has_active": bool(active),
        "matured_goats": matured_goats,
        "matured_kids": matured_kids,
        "principal": principal,
        "earnings": earnings,
        "available": available,
        "earliest_matured_at": earliest,
        "next_maturity_at": progress.get("next_maturity_at"),
        "progress_pct": int(progress.get("pct") or 0),
        "total_goats": int(total_goats or 0),
        "invested": invested if isinstance(invested, Decimal) else Decimal(str(invested or 0)),
    }


def _build_matured_projects(profile, my_projects: list[dict]) -> list[dict]:
    """Home-dashboard matured cards. CGF is one aggregated card when any cycle matured."""
    out: list[dict] = []
    try:
        cgf = _cgf_maturity_summary(profile)
    except Exception:
        cgf = None

    if cgf and cgf["has_matured"]:
        matured_n = cgf["matured_count"]
        active_n = cgf["active_count"]
        if active_n:
            cycle_line = (
                f"{matured_n} matured cycle{'s' if matured_n != 1 else ''} · "
                f"{active_n} still active"
            )
        else:
            cycle_line = (
                f"{matured_n} matured 14-month cycle{'s' if matured_n != 1 else ''} ready"
            )
        matured_on = _format_coop_date(cgf.get("earliest_matured_at"))
        out.append(
            {
                "id": "matured-cgf",
                "project_id": "cgf",
                "name": "Commercial Goat Farming",
                "short_name": "CGF",
                "icon": "fa-horse",
                "matured_on": matured_on,
                "cycle_line": cycle_line,
                "principal": cgf["principal"],
                "earnings": cgf["earnings"],
                "available_amount": cgf["available"],
                "next_best_action": "Transfer money to main account for withdrawal",
                "matured_goats": cgf["matured_goats"],
                "matured_kids": cgf["matured_kids"],
            }
        )

    # Matured personal 52WSC cycles awaiting decision or pot transfer.
    try:
        from savings_52_weeks.cycle_service import sync_member_cycles
        from savings_52_weeks.models import SavingsCycle

        sync_member_cycles(profile)
        wsc_cycle = (
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
        if wsc_cycle:
            principal = wsc_cycle.amount_saved or ZERO
            earnings = wsc_cycle.interest_earned or ZERO
            bf = wsc_cycle.balance_brought_forward or ZERO
            available = principal + earnings + bf
            matured_on = ""
            if wsc_cycle.matured_at:
                matured_on = timezone.localtime(
                    wsc_cycle.matured_at, timezone.get_default_timezone()
                ).strftime("%d %b %Y")
            elif wsc_cycle.end_date:
                matured_on = wsc_cycle.end_date.strftime("%d %b %Y")
            out.append(
                {
                    "id": f"matured-52wsc-{wsc_cycle.pk}",
                    "project_id": "52wsc",
                    "name": "52 Weeks Saving Challenge",
                    "short_name": "52WSC",
                    "icon": "fa-piggy-bank",
                    "matured_on": matured_on,
                    "cycle_line": (
                        f"{wsc_cycle.label} · started {wsc_cycle.start_date.strftime('%d %b %Y')}"
                    ),
                    "principal": principal,
                    "earnings": earnings,
                    "available_amount": available,
                    "next_best_action": (
                        "Start a new cycle with BF or transfer everything to Main Account"
                        if wsc_cycle.status == SavingsCycle.STATUS_AWAITING_DECISION
                        else "Transfer matured pot (saved + interest) to Main Account"
                    ),
                }
            )
    except Exception:
        pass

    _ = my_projects
    return out


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
            from savings_52_weeks.cycle_service import sync_member_cycles

            cycle_info = sync_member_cycles(profile)
            week = int(cycle_info.get("personalWeek") or _week_of_year())
            start_label = cycle_info.get("cycleStartDate") or "—"
            end_label = cycle_info.get("cycleEndDate") or "—"
            cycle_line = cycle_info.get("cycleLabel") or f"Week {week} of 52"
            cards.append(_card(
                "52 Weeks Saving Challenge", "fa-piggy-bank",
                invested=saved,
                status_tag=(
                    "Matured"
                    if cycle_info.get("maturedCycle")
                    else "Active"
                ),
                status_class=(
                    "st-matured" if cycle_info.get("maturedCycle") else "st-active"
                ),
                cycle_line=f"{cycle_line} · Week {week} of 52",
                url=_safe_reverse("savings_52_weeks:member_dashboard"),
                stats=[
                    {"label": "Saved this cycle", "value": saved, "cls": "locked", "badge": "Locked"},
                    {"label": "Interest earned", "value": interest, "cls": "green", "badge": ""},
                    {"label": "Matured (transferable)", "value": available, "cls": "green", "badge": ""},
                ],
                progress={
                    "pct": int(week / 52 * 100),
                    "left": f"Week {week} / 52",
                    "right": f"{start_label} → {end_label}",
                },
                transfer=({"label": "52 Weeks Saving Challenge", "suggested": available}
                          if available > ZERO else None),
            ))
        except Exception:
            pass

    # ---- Commercial Goat Farming ----
    if "Commercial Goat Farming" in names:
        try:
            cgf = _cgf_maturity_summary(profile)
            matured_n = cgf["matured_count"]
            active_n = cgf["active_count"]
            next_on = _format_coop_date(cgf.get("next_maturity_at"))
            if cgf["has_matured"] and cgf["has_active"]:
                status_tag = "Partially matured"
                status_class = "st-mixed"
                cycle_line = (
                    f"{matured_n} matured · {active_n} active"
                    + (f" · next matures {next_on}" if next_on else "")
                )
            elif cgf["has_matured"]:
                status_tag = "Matured"
                status_class = "st-matured"
                cycle_line = (
                    f"{matured_n} matured 14-month cycle{'s' if matured_n != 1 else ''}"
                )
            else:
                status_tag = "Active"
                status_class = "st-active"
                cycle_line = (
                    f"Matures on {next_on}" if next_on else "14-month cycle"
                )
            cards.append(_card(
                "Commercial Goat Farming", "fa-horse",
                invested=cgf["invested"],
                status_tag=status_tag,
                status_class=status_class,
                cycle_line=cycle_line,
                url=_safe_reverse("goat_farming:dashboard"),
                progress={"pct": int(cgf.get("progress_pct") or 0)},
                stats=[
                    {"label": "Amount invested", "value": cgf["invested"], "cls": "", "badge": ""},
                    {
                        "label": "Current goats",
                        "value": f"{cgf['total_goats']} goats",
                        "cls": "",
                        "badge": "",
                        "raw": True,
                    },
                    {
                        "label": "Matured cycles",
                        "value": f"{matured_n} of {matured_n + active_n}",
                        "cls": "",
                        "badge": "",
                        "raw": True,
                    },
                ],
                transfer=(
                    {"label": "Commercial Goat Farming", "suggested": cgf["available"]}
                    if cgf["has_matured"]
                    else None
                ),
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

    # ---- Real Estate Projects (single portfolio card) ----
    try:
        from realestate_projects.models import RealEstateProject
        projects = list(RealEstateProject.objects.filter(allowed_members=user).distinct())
        if projects:
            total_gross = ZERO
            total_withheld = ZERO
            total_available = ZERO
            running_count = 0
            closed_count = 0
            upcoming_count = 0
            for project in projects:
                status = getattr(project, "status", "")
                if status == "running":
                    running_count += 1
                elif status == "closed":
                    closed_count += 1
                elif status == "upcoming":
                    upcoming_count += 1
                bal = _rep_balances(user, project)
                total_gross += bal["gross"]
                total_withheld += bal["withheld"]
                total_available += bal["available"]

            status_label = "Active" if running_count else "Closed" if closed_count else "Upcoming"
            cycle_bits = []
            if running_count:
                cycle_bits.append(f"{running_count} running")
            if closed_count:
                cycle_bits.append(f"{closed_count} closed")
            if upcoming_count:
                cycle_bits.append(f"{upcoming_count} upcoming")
            cycle_line = " · ".join(cycle_bits) or f"{len(projects)} project(s)"

            cards.append(_card(
                "Real Estate Projects", "fa-city",
                invested=total_gross,
                status_tag=status_label,
                status_class="st-active" if running_count else "st-matured" if closed_count else "st-locked",
                cycle_line=cycle_line,
                url=_safe_reverse("realestate_projects:rep"),
                card_id="rep",
                stats=[
                    {
                        "label": "Projects",
                        "value": f"{len(projects)} project{'s' if len(projects) != 1 else ''}",
                        "cls": "",
                        "badge": "",
                        "raw": True,
                    },
                    {"label": "Total contributed", "value": total_gross, "cls": "", "badge": ""},
                    {"label": "Withheld", "value": total_withheld, "cls": "", "badge": ""},
                    {"label": "Refundable", "value": total_available, "cls": "green", "badge": ""},
                ],
                transfer=None,
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
        withheld = RealEstateProjectActionRequest.objects.defer(
            "main_account_transaction",
            "realestate_transaction",
            "processed_by",
        ).filter(
            user=user,
            project=project,
            status__in=[
                RealEstateProjectActionRequest.STATUS_PENDING,
                RealEstateProjectActionRequest.STATUS_APPROVED,
            ],
        ).aggregate(t=Sum("amount"))["t"] or ZERO
        deducted = ZERO
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
            dividend_claim_state,
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
                "coop_dividend_claim": dividend_claim_state(holding),
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
