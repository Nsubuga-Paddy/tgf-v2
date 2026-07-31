from __future__ import annotations

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.dashboard_service import build_member_dashboard
from help_center.models import HelpVideo

PROJECT_52WSC = "52 Weeks Saving Challenge"
PROJECT_CGF = "Commercial Goat Farming"
PROJECT_GWC = "Generational Wealth Creation"
PROJECT_REP = "Real Estate Projects"
TARGET_52WSC = Decimal("13780000")


def date_label(value) -> str:
    """Match Django template filters like date:\"M d, Y\"."""
    if not value:
        return "-"
    if isinstance(value, datetime):
        value = timezone.localtime(value).date()
    if isinstance(value, date):
        return value.strftime("%b %d, %Y")
    return str(value)


def gwc_date_label(value) -> str:
    """Day-first labels used on the GWC member page (e.g. 1 Mar 2026)."""
    if not value:
        return "-"
    if isinstance(value, datetime):
        value = timezone.localtime(value).date()
    if isinstance(value, date):
        return f"{value.day} {value.strftime('%b %Y')}"
    return str(value)


def calendar_week_of_year(today: date | None = None) -> int:
    """Same formula as savings_52_weeks member/group dashboards (Jan 1 based)."""
    today = today or date.today()
    days_elapsed = (today - date(today.year, 1, 1)).days
    return min(days_elapsed // 7 + 1, 52)


def money2(value) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def money(value) -> int:
    if value is None:
        return 0
    if isinstance(value, Decimal):
        return int(value.quantize(Decimal("1")))
    return int(value)


def ugx(value) -> str:
    return f"UGX {money(value):,}"


def compact_ugx(value) -> str:
    amount = money(value)
    if amount >= 1_000_000:
        exact = amount % 1_000_000 == 0
        return f"UGX {amount / 1_000_000:.{0 if exact else 1}f}M"
    if amount >= 1_000:
        return f"UGX {amount / 1_000:.0f}K"
    return ugx(amount)


def date_display(value) -> str:
    if not value:
        return ""
    if isinstance(value, datetime):
        value = timezone.localtime(value)
        return value.strftime("%d %b %Y")
    if isinstance(value, date):
        return value.strftime("%d %b %Y")
    return str(value)


def frontend_icon(icon: str) -> str:
    icon = icon or ""
    mapping = {
        "fa-piggy-bank": "piggy",
        "fa-hand-holding-heart": "heart",
        "fa-horse": "goat",
        "fa-city": "building",
        "fa-lock": "lock",
        "fa-users": "users",
        "fa-mug-hot": "coffee",
        "fa-seedling": "seedling",
        "fa-hand-holding-usd": "hand",
        "fa-landmark": "landmark",
        "fa-shield-alt": "shield",
        "fa-user-clock": "clock",
    }
    return mapping.get(icon, "piggy")


def project_id(name: str) -> str:
    lowered = (name or "").lower()
    if "52" in lowered:
        return "52wsc"
    if "generational" in lowered or "gwc" in lowered:
        return "gwc"
    if "goat" in lowered:
        return "cgf"
    if "real estate" in lowered:
        return "rep"
    if "fixed" in lowered:
        return "fsa"
    if "club" in lowered:
        return "clubs"
    if "coffee" in lowered:
        return "coffee"
    if "cocoa" in lowered:
        return "cocoa"
    if "loan" in lowered:
        return "loans"
    return lowered.replace(" ", "-")


def short_name(name: str) -> str:
    pid = project_id(name)
    return {
        "52wsc": "52WSC",
        "gwc": "GWC",
        "cgf": "CGF",
        "rep": "REP",
        "fsa": "FSA",
    }.get(pid, (name or "Project")[:8].upper())


def serialize_project_card(card: dict) -> dict:
    progress = card.get("progress") or {}
    return {
        "id": card.get("card_id") or project_id(card.get("name")),
        "name": card.get("name") or "Project",
        "shortName": short_name(card.get("name")),
        "icon": frontend_icon(card.get("icon")),
        "invested": money(card.get("invested")),
        "status": card.get("status_tag") or "Active",
        "cycleLine": card.get("cycle_line") or "",
        "progress": int(progress.get("pct") or 0),
        "stats": [
            {
                "label": stat.get("label") or "",
                "value": stat.get("value") if stat.get("raw") else compact_ugx(stat.get("value")),
            }
            for stat in card.get("stats", [])
        ],
    }


def serialize_discover(project: dict) -> dict:
    state = project.get("state")
    return {
        # Numeric Project.pk — required to submit ProjectAccessRequest.
        "id": project.get("id"),
        "slug": project_id(project.get("name")),
        "name": project.get("name") or "Project",
        "icon": frontend_icon(project.get("icon")),
        "summary": project.get("summary") or "More details coming soon.",
        "rate": project.get("rate") or "",
        "minEntry": project.get("min_entry") or "",
        "cycle": project.get("cycle") or "",
        "requestStatus": "pending" if state == "pending" else None,
        "availability": state,
        "wasRejected": bool(project.get("was_rejected")),
        "canRequest": state == "request",
    }


def item_value(item, key, default=None):
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def serialize_transaction(txn) -> dict:
    """Shape expected by React TransactionHistoryModal / downloadTransactionsCsv."""
    signed = item_value(txn, "signed_amount", None)
    if signed is None:
        raw_amount = item_value(txn, "amount") or 0
        direction = (item_value(txn, "direction") or "").lower()
        if direction == "debit":
            signed = -abs(Decimal(str(raw_amount)))
        else:
            signed = Decimal(str(raw_amount))
    amount = money(signed)

    category_key = item_value(txn, "category") or ""
    category_label = ""
    if hasattr(txn, "get_category_display"):
        try:
            category_label = txn.get_category_display()
        except Exception:
            category_label = str(category_key).replace("_", " ").title()
    else:
        category_label = str(category_key).replace("_", " ").title()

    title = (
        item_value(txn, "source_label")
        or item_value(txn, "label")
        or item_value(txn, "description")
        or category_label
        or "Transaction"
    )
    description = (item_value(txn, "description") or "").strip()
    meta_parts = [part for part in (category_label, description) if part and part != title]
    meta = " - ".join(meta_parts) if meta_parts else category_label or "Main account"

    created = item_value(txn, "created_at") or item_value(txn, "date")
    if isinstance(created, datetime):
        at_iso = timezone.localtime(created).isoformat()
    elif isinstance(created, date):
        at_iso = datetime.combine(created, datetime.min.time()).isoformat()
    else:
        at_iso = str(created) if created else ""

    return {
        "id": str(
            item_value(txn, "id")
            or item_value(txn, "reference")
            or at_iso
            or title
        ),
        "title": title,
        "label": title,
        "meta": meta,
        "at": at_iso,
        "ref": item_value(txn, "reference") or "",
        "amount": amount,
        "category": "in" if amount >= 0 else "out",
    }


def serialize_profile(user) -> dict:
    profile = user.profile
    return {
        "firstName": user.first_name or "",
        "lastName": user.last_name or "",
        "fullName": profile.display_name,
        "username": user.username,
        "email": user.email or "",
        "accountNumber": profile.account_number or "",
        "memberSince": date_display(profile.created_at),
        "whatsapp": str(profile.whatsapp_number or ""),
        "nationalId": profile.national_id or "",
        "address": profile.address or "",
        "birthdate": profile.birthdate.isoformat() if profile.birthdate else "",
        "bio": profile.bio or "",
        "isVerified": profile.is_verified,
        "bankName": profile.bank_name or "",
        "bankAccountNumber": profile.bank_account_number or "",
        "bankAccountName": profile.bank_account_name or "",
    }


def quantity(value) -> float:
    if value is None:
        return 0.0
    return float(value)


def serialize_shareholding_from_dashboard(ctx: dict) -> dict:
    """Map dashboard_service coop_* fields to the React shareholding shape."""
    summary = ctx.get("coop_summary") or {}
    is_shareholder = bool(ctx.get("is_shareholder"))
    return serialize_shareholding_summary(
        summary,
        is_shareholder=is_shareholder,
        election_open=bool(ctx.get("coop_election_open")),
        display_state="full" if is_shareholder else "no_access",
    )


def serialize_shareholding_summary(
    summary: dict | None,
    *,
    is_shareholder: bool,
    election_open: bool = False,
    display_state: str = "no_access",
) -> dict:
    """
    Align with cooperative_shareholding.services.build_shareholding_summary keys
    used by the Django dashboard/profile templates.
    """
    summary = summary or {}
    rate_pct = summary.get("dividend_rate_percent")
    if rate_pct is None and summary.get("dividend_rate") is not None:
        try:
            rate_pct = (Decimal(str(summary["dividend_rate"])) * Decimal("100")).quantize(
                Decimal("0.01")
            )
        except Exception:
            rate_pct = None

    shares_held = quantity(summary.get("total_shares"))
    dividend_eligible = quantity(summary.get("dividend_eligible_shares"))
    return {
        "isShareholder": is_shareholder,
        "displayState": display_state,
        "sharesHeld": shares_held,
        "sharesHeldDisplay": summary.get("total_shares_display")
        or (f"{shares_held:g}" if shares_held else "0"),
        "portfolioValue": money(summary.get("portfolio_value")),
        "dividendEligible": dividend_eligible,
        "dividendEligibleDisplay": summary.get("dividend_eligible_shares_display")
        or (f"{dividend_eligible:g}" if dividend_eligible else "0"),
        "dividendEligibleValue": money(summary.get("dividend_eligible_value")),
        "expectedDividend": money(summary.get("expected_dividend")),
        "dividendRate": f"{rate_pct}%" if rate_pct is not None else "",
        "dividendRatePercent": float(rate_pct) if rate_pct is not None else 0,
        "certificateStatus": summary.get("certificate_status") or "",
        "certificateNumber": "",
        "memberSince": summary.get("year_joined") or "",
        "yearJoined": summary.get("year_joined") or "",
        "electionOpen": election_open,
        "electionDeadline": "",
        "equityBadge": "Shareholder" if is_shareholder else "Member",
        "tier": summary.get("tier") or "",
        "tierEmoji": summary.get("tier_emoji") or "",
        "newEraShares": quantity(summary.get("new_era_shares")),
        "newEraSharesDisplay": summary.get("new_era_shares_display") or "0",
        "newEraValue": money(summary.get("new_era_value")),
        "newSharePurchasePrice": money(summary.get("new_share_purchase_price")),
        "legacyValuePerShare": money(summary.get("legacy_value_per_share")),
        "totalDividendsEarned": 0,
        "issuancePeriodName": summary.get("issuance_period_name") or "",
    }


def _action_tone(project: str) -> str:
    key = (project or "").lower()
    if key in {"52wsc", "wsc"}:
        return "wsc"
    if key == "cgf":
        return "cgf"
    if "real estate" in key or key == "rep":
        return "rep"
    if key in {"cooperative", "platform", "clubs"}:
        return "coop"
    if key == "main":
        return "main"
    return "coop"


def _sort_dt(value):
    if not value:
        return timezone.now()
    if timezone.is_aware(value):
        return value
    return timezone.make_aware(value)


def build_action_requests(profile) -> list[dict]:
    """Mirror Django ProfileView's all_action_requests for the React profile panel."""
    from accounts.models import ProjectAccessRequest
    from realestate_projects.models import RealEstateProjectActionRequest

    rows: list[dict] = []

    def add(
        *,
        req_id: str,
        project: str,
        type_label: str,
        detail: str,
        status: str,
        status_display: str,
        created_at,
    ):
        rows.append(
            {
                "id": req_id,
                "project": project,
                "typeLabel": type_label,
                "detail": detail,
                "status": (status or "").lower(),
                "statusDisplay": status_display,
                "createdAt": date_display(created_at),
                "tone": _action_tone(project),
                "_sort": _sort_dt(created_at),
            }
        )

    for r in profile.withdrawal_requests.all().order_by("-created_at"):
        add(
            req_id=f"w52-wd-{r.pk}",
            project="52WSC",
            type_label="Withdrawal",
            detail=ugx(r.amount),
            status=r.status,
            status_display=r.get_status_display(),
            created_at=r.created_at,
        )

    for r in profile.gwc_contributions.all().order_by("-created_at"):
        add(
            req_id=f"w52-gwc-{r.pk}",
            project="52WSC",
            type_label="Transfer to GWC",
            detail=ugx(r.amount),
            status=r.status,
            status_display=r.get_status_display(),
            created_at=r.created_at,
        )

    for r in profile.project_access_requests.select_related("project").order_by("-created_at"):
        detail = r.project.name
        if r.member_notes:
            detail += f" · {r.member_notes[:80]}"
        if r.status == ProjectAccessRequest.STATUS_REJECTED and r.admin_notes:
            detail += f" · Reason: {r.admin_notes}"
        add(
            req_id=f"par-{r.pk}",
            project="Platform",
            type_label="Project access",
            detail=detail,
            status=r.status,
            status_display=r.get_status_display(),
            created_at=r.created_at,
        )

    for r in profile.cgf_action_requests.all().order_by("-created_at"):
        detail = f"{r.goats_count or 0} goats"
        if r.request_type == "sell_cash_out":
            detail += f" · {ugx(r.cash_value)}"
        type_map = {
            "sell_cash_out": "Sell & Cash Out",
            "take_goats": "Take Goats",
            "transfer": "Transfer",
        }
        add(
            req_id=f"cgf-{r.pk}",
            project="CGF",
            type_label=type_map.get(r.request_type, r.request_type),
            detail=detail,
            status=r.status,
            status_display=r.get_status_display(),
            created_at=r.created_at,
        )

    for r in profile.user.realestate_action_requests.all().order_by("-created_at"):
        type_map = {
            RealEstateProjectActionRequest.ACTION_WITHDRAW: "Withdraw from Real Estate",
            RealEstateProjectActionRequest.ACTION_TRANSFER_GWC: "Transfer to GWC",
            RealEstateProjectActionRequest.ACTION_TRANSFER_NAMAYUMBA: "Transfer to Namayumba estate",
        }
        add(
            req_id=f"rep-{r.pk}",
            project="Real Estate",
            type_label=type_map.get(r.action_type, r.action_type),
            detail=f"{r.project.name} · {ugx(r.amount)}",
            status=r.status,
            status_display=r.get_status_display(),
            created_at=r.created_at,
        )

    # Main-account ledger requests (newer than legacy 52WSC withdrawals)
    if hasattr(profile, "main_account_withdrawals"):
        for r in profile.main_account_withdrawals.all().order_by("-created_at"):
            add(
                req_id=f"main-wd-{r.pk}",
                project="MAIN",
                type_label="Main account withdrawal",
                detail=ugx(r.amount),
                status=r.status,
                status_display=r.get_status_display(),
                created_at=r.created_at,
            )

    if hasattr(profile, "project_transfer_requests"):
        for r in profile.project_transfer_requests.all().order_by("-created_at"):
            add(
                req_id=f"xfer-{r.pk}",
                project="MAIN",
                type_label="Transfer to main",
                detail=f"{r.project_label} · {ugx(r.amount)}",
                status=r.status,
                status_display=r.get_status_display(),
                created_at=r.created_at,
            )

    try:
        coop_holding = profile.user.cooperative_shareholding
    except Exception:
        coop_holding = None

    if coop_holding:
        from cooperative_shareholding.models import DividendAllocationLine

        for sub in coop_holding.dividend_choices.prefetch_related("allocation_lines").order_by(
            "-created_at"
        ):
            for line in sub.allocation_lines.all():
                add(
                    req_id=f"coop-div-{sub.pk}-{line.pk}",
                    project="Cooperative",
                    type_label=f"Dividend - {line.get_action_type_display()}",
                    detail=ugx(line.amount),
                    status=sub.status,
                    status_display=sub.get_status_display(),
                    created_at=sub.created_at,
                )

    rows.sort(key=lambda item: item["_sort"], reverse=True)
    for item in rows:
        item.pop("_sort", None)
    return rows


def build_profile_shareholding(profile) -> dict:
    """Mirror ProfileView cooperative shareholding context for the React profile page."""
    try:
        from cooperative_shareholding.services import (
            build_shareholding_summary,
            cooperative_display_state,
        )
    except Exception:
        return serialize_shareholding_summary(
            None, is_shareholder=False, display_state="no_access"
        )

    holding = None
    try:
        holding = profile.user.cooperative_shareholding
    except Exception:
        holding = None

    display_state = cooperative_display_state(profile, holding)
    if display_state != "full" or holding is None:
        return serialize_shareholding_summary(
            None,
            is_shareholder=False,
            display_state=display_state,
        )

    summary = build_shareholding_summary(holding)
    return serialize_shareholding_summary(
        summary,
        is_shareholder=True,
        election_open=bool(getattr(holding, "dividend_election_open", False)),
        display_state="full",
    )


class DashboardAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        ctx = build_member_dashboard(request.user)
        member_profile = request.user.profile
        shareholding = serialize_shareholding_from_dashboard(ctx)
        # Keep portfolio value in sync with dashboard_service even if summary is empty.
        if ctx.get("coop_portfolio_value") is not None:
            shareholding["portfolioValue"] = money(ctx.get("coop_portfolio_value"))
        if ctx.get("coop_year_joined"):
            shareholding["memberSince"] = ctx.get("coop_year_joined")
            shareholding["yearJoined"] = ctx.get("coop_year_joined")
        is_shareholder = bool(shareholding.get("isShareholder"))
        dashboard = {
            "member": {
                "firstName": ctx.get("first_name") or request.user.first_name or request.user.username,
                "fullName": ctx.get("member_name") or member_profile.display_name,
                "initials": ctx.get("initials") or member_profile.initials,
                "accountNumber": ctx.get("account_number") or member_profile.account_number or "",
                "isVerified": bool(ctx.get("is_verified")),
                "isShareholder": is_shareholder,
            },
            "mainAccount": {
                "available": money(ctx.get("main_available")),
                "posted": money(ctx.get("main_posted")),
                "pendingWithdrawal": money(ctx.get("main_pending_withdrawal")),
            },
            "lifetime": {
                "totalInvestedEver": money(ctx.get("total_invested")),
                "totalWithdrawnEver": 0,
            },
            "shareholding": shareholding,
            "myProjects": [serialize_project_card(card) for card in ctx.get("my_projects", [])],
            "otherProjects": [serialize_discover(project) for project in ctx.get("discover_projects", [])],
            "pendingRequests": [
                {"id": f"pending-{i}", "label": "Pending request", "detail": ""}
                for i in range(int(ctx.get("pending_count") or 0))
            ],
            "transactions": [serialize_transaction(txn) for txn in ctx.get("transactions", [])],
            "totals": {
                "totalPortfolio": money(ctx.get("total_portfolio")),
                "invested": money(ctx.get("total_invested")),
            },
            "profile": serialize_profile(request.user),
        }
        return Response(dashboard)


class ProfileAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile = request.user.profile
        granted = list(profile.projects.values_list("name", flat=True))
        access_requests = [
            {
                "id": f"par-{req.pk}",
                "project": req.project.name,
                "status": req.status,
                "statusDisplay": req.get_status_display(),
                "createdAt": date_display(req.created_at),
                "adminNotes": req.admin_notes or "",
            }
            for req in profile.project_access_requests.select_related("project").order_by("-created_at")[:20]
        ]
        requestable = [
            {"id": project_id(project.name), "name": project.name}
            for project in profile.projects.model.objects.filter(is_public=True, accepts_requests=True)
            .exclude(pk__in=profile.projects.values_list("pk", flat=True))
            .order_by("sort_order", "name")
        ]
        shareholding = build_profile_shareholding(profile)
        return Response(
            {
                "profile": serialize_profile(request.user),
                "grantedProjects": granted,
                "requestableProjects": requestable,
                "projectAccessRequests": access_requests,
                "actionRequests": build_action_requests(profile),
                "shareholding": shareholding,
                "isShareholder": bool(shareholding.get("isShareholder")),
            }
        )

    def patch(self, request):
        user = request.user
        profile = user.profile
        data = request.data
        for attr, field in (
            ("firstName", "first_name"),
            ("lastName", "last_name"),
            ("email", "email"),
        ):
            if attr in data:
                setattr(user, field, (data.get(attr) or "").strip())
        for attr, field in (
            ("nationalId", "national_id"),
            ("address", "address"),
            ("bio", "bio"),
            ("bankName", "bank_name"),
            ("bankAccountNumber", "bank_account_number"),
            ("bankAccountName", "bank_account_name"),
        ):
            if attr in data:
                setattr(profile, field, (data.get(attr) or "").strip() or None)
        if "whatsapp" in data:
            profile.whatsapp_number = (data.get("whatsapp") or "").strip()
        if "birthdate" in data:
            value = (data.get("birthdate") or "").strip()
            try:
                profile.birthdate = date.fromisoformat(value) if value else None
            except ValueError:
                pass
        try:
            profile.full_clean(exclude=["photo"])
        except DjangoValidationError as exc:
            return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)
        user.save()
        profile.save()
        return Response({"profile": serialize_profile(user)})


def build_52wsc_member_payload(profile) -> dict:
    """Reuse the same calculations as savings_52_weeks.views.member_savings."""
    from savings_52_weeks.interest_utils import calculate_unfixed_interest_ytd
    from savings_52_weeks.models import Investment, SavingsTransaction

    Investment.check_all_investments_status(user_profile=profile)

    all_transactions = profile.savings_transactions.all().order_by(
        "transaction_date", "created_at"
    )

    total_deposits = Decimal("0.00")
    total_withdrawals = Decimal("0.00")
    total_gwc = Decimal("0.00")
    for transaction in all_transactions:
        if transaction.transaction_type == "deposit":
            total_deposits += transaction.amount
        elif transaction.transaction_type == "withdrawal":
            total_withdrawals += transaction.amount
        elif transaction.transaction_type == "gwc_contribution":
            total_gwc += transaction.amount

    net_deposits = total_deposits - total_withdrawals - total_gwc
    current_year = timezone.now().year
    challenge_progress = SavingsTransaction.get_user_challenge_progress(
        profile, year=current_year
    )

    latest_transaction_all_types = (
        profile.savings_transactions.all().order_by("-created_at").first()
    )
    latest_deposit_transaction = profile.savings_transactions.filter(
        transaction_type="deposit",
        transaction_date__year=current_year,
    ).order_by("-created_at").first()

    if latest_transaction_all_types:
        if latest_transaction_all_types.transaction_type in (
            "withdrawal",
            "gwc_contribution",
        ):
            balance_brought_forward = Decimal("0.00")
        else:
            balance_brought_forward = (
                latest_transaction_all_types.remaining_balance or Decimal("0.00")
            )
    else:
        balance_brought_forward = Decimal("0.00")

    running_total = Decimal("0.00")
    txn_rows = []
    for transaction in all_transactions:
        if transaction.transaction_type == "deposit":
            running_total += transaction.amount
        elif transaction.transaction_type in ("withdrawal", "gwc_contribution"):
            running_total -= transaction.amount

        weeks_covered = "-"
        if (
            transaction.transaction_type == "deposit"
            and transaction.fully_covered_weeks
        ):
            weeks_covered = ", ".join(
                f"Week {week_data.get('week')}"
                for week_data in transaction.fully_covered_weeks
                if week_data.get("week") is not None
            ) or "-"

        signed = transaction.amount
        if transaction.transaction_type in ("withdrawal", "gwc_contribution"):
            signed = -abs(transaction.amount)

        balance_forward = None
        if transaction.transaction_type == "deposit":
            balance_forward = money(transaction.remaining_balance)

        txn_rows.append(
            {
                "id": f"tx-{transaction.pk}",
                "date": date_label(transaction.transaction_date),
                "type": transaction.get_transaction_type_display().title(),
                "typeKey": transaction.transaction_type,
                "amount": money(signed),
                "runningTotal": money(running_total),
                "weeksCovered": weeks_covered,
                "receipt": transaction.receipt_number or "—",
                "balanceForward": balance_forward,
            }
        )

    transactions = list(reversed(txn_rows[-10:]))

    investments_qs = profile.investments.all()
    fixed_investments = [inv for inv in investments_qs if inv.status == "fixed"]
    total_invested = sum(
        (inv.amount_invested for inv in fixed_investments), Decimal("0.00")
    )
    total_interest_expected = sum(
        (inv.total_interest_expected for inv in fixed_investments), Decimal("0.00")
    )
    uninvested_amount = (
        net_deposits - total_invested
        if net_deposits > total_invested
        else Decimal("0.00")
    )
    latest_investment = (
        investments_qs.filter(status="fixed").order_by("-start_date").first()
    )
    latest_maturity_date = (
        latest_investment.maturity_date if latest_investment else None
    )

    unfixed_interest_earned_ytd = calculate_unfixed_interest_ytd(profile)
    daily_unfixed_interest = (
        (uninvested_amount * Decimal("0.15") / Decimal("365")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if uninvested_amount
        else Decimal("0.00")
    )

    current_week = calendar_week_of_year()
    required_savings = current_week * 10000
    remaining_weeks = max(52 - current_week, 0)

    current_year_deposits = Decimal("0.00")
    for t in all_transactions.filter(
        transaction_date__year=current_year, transaction_type="deposit"
    ):
        current_year_deposits += t.amount

    progress_percentage = float(
        min(
            (current_year_deposits / TARGET_52WSC * 100) if TARGET_52WSC > 0 else 0,
            100,
        )
    )

    weeks_completed = int(challenge_progress.get("weeks_completed") or 0)
    total_weeks = int(challenge_progress.get("total_weeks") or 52)
    next_week_to_cover = (
        latest_deposit_transaction.next_week if latest_deposit_transaction else 1
    )
    cycle_complete = weeks_completed >= total_weeks or next_week_to_cover > total_weeks

    investment_list = [
        {
            "id": f"inv-{inv.pk}",
            "startDate": date_label(inv.start_date),
            "amount": money(inv.amount_invested),
            "interestRate": f"{inv.interest_rate}%",
            "interestEarned": money(inv.interest_gained_so_far),
            "expectedInterest": money(inv.total_interest_expected),
            "maturityDate": date_label(inv.maturity_date),
            "status": inv.get_status_display().title()
            if hasattr(inv, "get_status_display")
            else str(inv.status).title(),
        }
        for inv in investments_qs.order_by("-start_date", "-pk")
    ]

    return {
        "member": {
            "accountNumber": profile.account_number or "",
            "targetAmount": money(TARGET_52WSC),
            "currentYearDeposits": money(current_year_deposits),
            "progressPercentage": progress_percentage,
            "balanceBroughtForward": money(balance_brought_forward),
            "weeksCompleted": weeks_completed,
            "nextWeekToCover": next_week_to_cover,
            "totalWeeks": total_weeks,
            "cycleComplete": cycle_complete,
            "fixedSavings": {
                "totalInvested": money(total_invested),
                "totalInterestExpected": money(total_interest_expected),
                "dailyUnfixedInterest": money2(daily_unfixed_interest),
                "unfixedInterestEarnedYtd": money(unfixed_interest_earned_ytd),
                "latestMaturityDate": date_label(latest_maturity_date)
                if latest_maturity_date
                else "-",
            },
            "weeklyTarget": {
                "currentWeek": current_week,
                "requiredSavings": required_savings,
                "remainingWeeks": remaining_weeks,
            },
        },
        "investments": investment_list,
        "transactions": transactions,
    }


class Savings52APIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile = request.user.profile
        if not profile.has_project(PROJECT_52WSC):
            return Response(
                {"detail": "You do not have access to the 52 Weeks Saving Challenge."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(build_52wsc_member_payload(profile))


def build_cgf_member_payload(profile) -> dict:
    """Reuse the same calculations as goat_farming.views.cgf_dashboard."""
    from datetime import timedelta

    from django.db.models import Sum

    from goat_farming.models import PackagePurchase, Payment, UserFarmAccount

    user_farm_accounts = (
        UserFarmAccount.objects.filter(user=profile, is_active=True)
        .select_related("farm")
        .order_by("farm__name", "created_at")
    )
    package_purchases = (
        PackagePurchase.objects.filter(user=profile)
        .select_related("package", "farm")
        .order_by("-purchase_date")
    )

    total_invested = package_purchases.aggregate(total=Sum("total_amount"))["total"] or 0
    total_paid = package_purchases.aggregate(total=Sum("amount_paid"))["total"] or 0
    total_balance = total_invested - total_paid
    total_goats = user_farm_accounts.aggregate(total=Sum("current_goats"))["total"] or 0

    allocated_purchases = package_purchases.filter(status="allocated").select_related(
        "package"
    )
    package_based_total = sum(
        p.goats_allocated * getattr(p.package, "kids_per_goat", 2)
        for p in allocated_purchases
    )
    effective_kids_per_goat = (package_based_total / total_goats) if total_goats else 0

    next_maturity_date = None
    if user_farm_accounts.exists():
        earliest_account = user_farm_accounts.order_by("created_at").first()
        if earliest_account:
            maturity_date = earliest_account.created_at + timedelta(days=425)
            if maturity_date > timezone.now():
                next_maturity_date = maturity_date

    farm_accounts = []
    total_expected_kids = 0
    for account in user_farm_accounts:
        resolved_kids = (
            account.expected_kids
            if account.expected_kids is not None
            else int(account.current_goats * effective_kids_per_goat)
        )
        total_expected_kids += resolved_kids
        created_local = timezone.localtime(account.created_at)
        farm_accounts.append(
            {
                "id": f"fa-{account.pk}",
                "farmName": account.farm.name,
                "farmLocation": account.farm.location or "",
                "currentGoats": int(account.current_goats or 0),
                "expectedKids": int(resolved_kids),
                "createdAt": created_local.date().isoformat(),
            }
        )

    purchases = []
    for purchase in package_purchases:
        purchases.append(
            {
                "id": purchase.pk,
                "farmName": purchase.farm.name if purchase.farm else "-",
                "packageName": purchase.package.name if purchase.package else "-",
                "totalAmount": money(purchase.total_amount),
                "amountPaid": money(purchase.amount_paid),
                "balanceDue": money(purchase.balance_due),
                "status": purchase.status,
                "statusLabel": purchase.get_status_display(),
                "goatsAllocated": int(purchase.goats_allocated or 0),
                "goatCount": int(purchase.package.goat_count if purchase.package else 0),
                "kidsPerGoat": int(
                    getattr(purchase.package, "kids_per_goat", 2) if purchase.package else 2
                ),
                "purchaseDate": date_label(purchase.purchase_date),
            }
        )

    all_payments = (
        Payment.objects.filter(purchase__user=profile)
        .select_related("purchase", "purchase__package", "purchase__farm")
        .order_by("-payment_date", "-created_at")
    )
    payments = []
    for payment in all_payments:
        purchase = payment.purchase
        package_name = purchase.package.name if purchase and purchase.package else "-"
        farm_name = purchase.farm.name if purchase and purchase.farm else "-"
        payments.append(
            {
                "id": payment.pk,
                "paymentDate": date_label(payment.payment_date),
                "receiptNumber": payment.receipt_number or "-",
                "amount": money(payment.amount),
                "paymentMethod": payment.payment_method or "Not specified",
                "packageName": package_name,
                "farmName": farm_name,
                "purchaseStatus": purchase.status if purchase else "",
                "notes": payment.notes or "",
                "processedBy": "System",
                "processedDate": date_label(payment.created_at),
            }
        )

    # Match goat_farming.views.transactions_page totals (sum of payments vs package totals)
    total_investments = all_payments.aggregate(total=Sum("amount"))["total"] or 0
    investment_count = all_payments.count()
    total_pending_amount = total_invested - total_investments

    return {
        "member": {
            "accountNumber": profile.account_number or "",
            "totalGoats": int(total_goats or 0),
            "totalInvested": money(total_invested),
            "totalPaid": money(total_paid),
            "totalBalance": money(total_balance),
            "totalExpectedKids": int(total_expected_kids),
            "nextMaturityDate": date_label(next_maturity_date)
            if next_maturity_date
            else None,
            "totalInvestments": money(total_investments),
            "investmentCount": int(investment_count),
            "totalPackageAmounts": money(total_invested),
            "totalPendingAmount": money(max(total_pending_amount, 0)),
        },
        "farmAccounts": farm_accounts,
        "purchases": purchases,
        "payments": payments,
    }


class CgfAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile = request.user.profile
        if not profile.has_project(PROJECT_CGF):
            return Response(
                {"detail": "You do not have access to Commercial Goat Farming."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(build_cgf_member_payload(profile))


def build_gwc_member_payload(user) -> dict:
    """Reuse gwc.services calculations used by the Django GWC dashboard."""
    from gwc.models import GWCFixedDeposit
    from gwc.services import (
        deposit_to_display,
        portfolio_summary_for_user,
        recent_activities_for_user,
    )

    profile = user.profile
    deposits_qs = GWCFixedDeposit.objects.filter(user=user).order_by("-start_date", "-pk")
    deposit_rows = []
    for deposit in deposits_qs:
        row = deposit_to_display(deposit)
        deposit_rows.append(
            {
                "depositId": row["deposit_id"],
                "status": row["status"],
                "isUpcoming": bool(row["is_upcoming"]),
                "principalAmount": money(row["principal_amount"]),
                "interestRate": float(row["interest_rate"] or 0),
                "interestMethod": row["interest_method"] or "",
                "compoundingFrequency": row["compounding_frequency"] or "",
                "dailyInterest": money(row["daily_interest"]),
                "monthlyInterest": money(row["monthly_interest"]),
                "projectedMaturityAmount": money(row["projected_maturity_amount"]),
                "accruedInterest": money(row["accrued_interest"]),
                "completionPercent": int(row["completion_percent"] or 0),
                "elapsedDurationDisplay": row["elapsed_duration_display"],
                "remainingDurationDisplay": row["remaining_duration_display"],
                "transactionDate": gwc_date_label(row["transaction_date"]),
                "startDate": gwc_date_label(row["start_date"]),
                "maturityDate": gwc_date_label(row["maturity_date"]),
                "tenureDisplay": row["tenure_display"],
                "payoutStructureDisplay": row["payout_structure_display"] or "At maturity",
                "interestAtMaturityAfterTax": money(row["interest_at_maturity_after_tax"]),
            }
        )

    portfolio = portfolio_summary_for_user(user)
    activities = []
    for index, activity in enumerate(recent_activities_for_user(user, limit=25)):
        activities.append(
            {
                "id": f"gwc-act-{index}-{activity.get('deposit_id') or 'x'}",
                "description": activity.get("description") or "",
                "timestamp": activity.get("timestamp") or "",
                "depositId": activity.get("deposit_id") or "",
                "type": activity.get("type") or "info",
                "amount": money(activity.get("amount"))
                if activity.get("amount") is not None
                else None,
            }
        )

    matured_count = sum(1 for d in deposit_rows if d["status"] == "Matured")
    return {
        "account": {
            "accountNumber": profile.account_number or "",
        },
        "portfolio": {
            "totalPrincipal": money(portfolio.get("total_principal")),
            "totalAccruedInterest": money(portfolio.get("total_accrued_interest")),
            "totalMaturityValue": money(portfolio.get("total_maturity_value")),
        },
        "deposits": deposit_rows,
        "activities": activities,
        "meta": {
            "canTransferToMain": matured_count > 0,
            "maturedCount": matured_count,
        },
    }


class GwcAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile = request.user.profile
        if not profile.has_project(PROJECT_GWC):
            return Response(
                {"detail": "You do not have access to Generational Wealth Creation."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(build_gwc_member_payload(request.user))


def _serialize_rep_list_project(project, *, user, pending_join_ids, interested_ids) -> dict:
    has_access = project.allowed_members.filter(pk=user.pk).exists()
    status_value = project.status
    if status_value == "running":
        if has_access:
            membership_state = "joined"
        elif project.pk in pending_join_ids:
            membership_state = "pending"
        else:
            membership_state = "available"
    elif status_value == "upcoming":
        membership_state = (
            "interested" if project.pk in interested_ids else "interest-available"
        )
    else:
        membership_state = "joined" if has_access else "available"

    payload = {
        "id": project.pk,
        "name": project.name,
        "location": project.location or "",
        "description": project.description or "",
        "status": status_value,
        "startDate": gwc_date_label(project.start_date),
        "endDate": gwc_date_label(project.end_date),
        "minimumInvestment": project.minimum_investment or "",
        "membersCount": int(getattr(project, "members_count", 0) or 0),
        "userHasAccess": has_access,
        "membershipState": membership_state,
        "showInSidebar": bool(project.show_in_sidebar),
    }
    if not has_access and status_value != "upcoming":
        # Match Django: hide restricted details from non-members.
        payload["description"] = ""
        payload["minimumInvestment"] = ""
        payload["membersCount"] = 0
    return payload


def build_rep_list_payload(user) -> dict:
    """Mirror realestate_projects.views.real_estate_projects_dashboard."""
    from django.db.models import Count

    from realestate_projects.models import (
        RealEstateProject,
        RealEstateProjectInterest,
        RealEstateProjectJoinRequest,
    )

    profile = user.profile
    running_projects = list(
        RealEstateProject.objects.filter(status=RealEstateProject.STATUS_RUNNING)
        .annotate(members_count=Count("allowed_members", distinct=True))
        .distinct()
    )
    closed_projects = list(
        RealEstateProject.objects.filter(status=RealEstateProject.STATUS_CLOSED)
        .annotate(members_count=Count("allowed_members", distinct=True))
        .distinct()
    )
    upcoming_projects = list(
        RealEstateProject.objects.filter(status=RealEstateProject.STATUS_UPCOMING).distinct()
    )

    pending_join_ids = set(
        RealEstateProjectJoinRequest.objects.filter(
            user=user,
            status=RealEstateProjectJoinRequest.STATUS_PENDING,
        ).values_list("project_id", flat=True)
    )
    interested_ids = set(
        RealEstateProjectInterest.objects.filter(user=user).values_list(
            "project_id", flat=True
        )
    )

    running = [
        _serialize_rep_list_project(
            project, user=user, pending_join_ids=pending_join_ids, interested_ids=interested_ids
        )
        for project in running_projects
    ]
    closed = [
        _serialize_rep_list_project(
            project, user=user, pending_join_ids=pending_join_ids, interested_ids=interested_ids
        )
        for project in closed_projects
    ]
    upcoming = [
        _serialize_rep_list_project(
            project, user=user, pending_join_ids=pending_join_ids, interested_ids=interested_ids
        )
        for project in upcoming_projects
    ]
    sidebar = [
        {"id": p["id"], "name": p["name"], "location": p["location"]}
        for p in running
        if p.get("showInSidebar")
    ]

    return {
        "member": {
            "accountNumber": profile.account_number or "",
            "firstName": user.first_name or user.username,
        },
        "runningProjects": running,
        "closedProjects": closed,
        "upcomingProjects": upcoming,
        "sidebarProjects": sidebar,
    }


def build_rep_detail_payload(user, project) -> dict:
    """Mirror realestate_projects.views.project_detail."""
    from django.db.models import Sum

    from realestate_projects.models import RealEstateProjectTransaction

    profile = user.profile
    user_has_access = project.allowed_members.filter(pk=user.pk).exists()
    transactions = RealEstateProjectTransaction.objects.filter(project=project)

    completed_user_ids = set(
        transactions.filter(
            payment_status=RealEstateProjectTransaction.PAYMENT_STATUS_FULL,
        )
        .values_list("user_id", flat=True)
        .distinct()
    )
    all_transaction_user_ids = set(transactions.values_list("user_id", flat=True).distinct())
    partial_user_ids = all_transaction_user_ids - completed_user_ids

    completed_payments_total = (
        transactions.filter(
            payment_status=RealEstateProjectTransaction.PAYMENT_STATUS_FULL,
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )
    partial_payments_total = (
        transactions.filter(
            payment_status=RealEstateProjectTransaction.PAYMENT_STATUS_PARTIAL,
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )

    user_transactions = RealEstateProjectTransaction.objects.filter(
        project=project,
        user=user,
    ).order_by("-created_at")

    user_total_paid = Decimal("0")
    for txn in user_transactions:
        if txn.type in (
            RealEstateProjectTransaction.TYPE_PAYMENT,
            RealEstateProjectTransaction.TYPE_ADJUSTMENT,
        ):
            user_total_paid += txn.amount
        elif txn.type == RealEstateProjectTransaction.TYPE_REFUND:
            user_total_paid -= txn.amount

    latest_user_txn = user_transactions.first()
    user_pending_balance = (
        latest_user_txn.balance_after
        if latest_user_txn and latest_user_txn.balance_after is not None
        else None
    )
    user_payment_completed = user_transactions.filter(
        payment_status=RealEstateProjectTransaction.PAYMENT_STATUS_FULL
    ).exists()

    vendor = project.vendor_total_amount
    ops = project.operational_costs
    total_budget = None
    if vendor is not None or ops is not None:
        total_budget = (vendor or Decimal("0")) + (ops or Decimal("0"))

    project_payload = {
        "id": project.pk,
        "name": project.name,
        "location": project.location or "",
        "status": project.status,
        "startDate": gwc_date_label(project.start_date),
        "endDate": gwc_date_label(project.end_date),
        "userHasAccess": user_has_access,
        "landSize": float(project.land_size) if project.land_size is not None else None,
        "landSizeUnit": project.land_size_unit or "",
        "vendorTotalAmount": money(vendor) if vendor is not None else None,
        "operationalCosts": money(ops) if ops is not None else None,
        "totalBudget": money(total_budget) if total_budget is not None else None,
        "completedMembersCount": len(completed_user_ids) if user_has_access else 0,
        "completedPaymentsTotal": money(completed_payments_total) if user_has_access else 0,
        "incompleteMembersCount": len(partial_user_ids) if user_has_access else 0,
        "partialPaymentsTotal": money(partial_payments_total) if user_has_access else 0,
    }

    txn_rows = []
    for txn in user_transactions:
        txn_date = txn.transaction_date or (
            timezone.localtime(txn.created_at).date() if txn.created_at else None
        )
        txn_rows.append(
            {
                "id": txn.pk,
                "date": gwc_date_label(txn_date),
                "amount": money(txn.amount),
                "acquisitionQuantity": float(txn.acquisition_quantity)
                if txn.acquisition_quantity is not None
                else None,
                "acquisitionUnit": txn.acquisition_unit or "",
                "balanceAfter": money(txn.balance_after)
                if txn.balance_after is not None
                else None,
                "paymentStatus": txn.payment_status,
                "type": txn.type,
            }
        )

    return {
        "member": {
            "accountNumber": profile.account_number or "",
            "firstName": user.first_name or user.username,
        },
        "project": project_payload,
        "user": {
            "totalPaid": money(user_total_paid),
            "pendingBalance": money(user_pending_balance)
            if user_pending_balance is not None
            else None,
            "paymentCompleted": bool(user_payment_completed),
        },
        "transactions": txn_rows,
    }


class RepListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile = request.user.profile
        if not profile.has_project(PROJECT_REP):
            return Response(
                {"detail": "You do not have access to Real Estate Projects."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(build_rep_list_payload(request.user))


class RepDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, project_id):
        from realestate_projects.models import RealEstateProject

        profile = request.user.profile
        if not profile.has_project(PROJECT_REP):
            return Response(
                {"detail": "You do not have access to Real Estate Projects."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            project = RealEstateProject.objects.get(pk=project_id)
        except (RealEstateProject.DoesNotExist, ValueError, TypeError):
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(build_rep_detail_payload(request.user, project))


class ProjectAccessRequestAPIView(APIView):
    """Dashboard 'Request access' for verified members (Django landing POST)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from accounts.project_access import (
            build_submission_messages,
            submit_project_access_requests,
        )

        profile = request.user.profile
        if not profile.is_verified:
            return Response(
                {
                    "detail": (
                        "Complete account verification before requesting project access."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        data = request.data or {}
        project_ids = data.get("projectIds") or data.get("project_ids") or []
        member_notes = data.get("memberNotes") or data.get("member_notes") or ""
        if not isinstance(project_ids, (list, tuple)):
            project_ids = [project_ids]
        if not project_ids:
            return Response(
                {"detail": "Select a project to request access."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = submit_project_access_requests(profile, list(project_ids), member_notes)
        messages_out = [
            {"level": level, "text": text}
            for level, text in build_submission_messages(result)
        ]
        return Response(
            {
                "ok": bool(result.get("created")),
                "messages": messages_out,
                "createdCount": len(result.get("created") or []),
            },
            status=status.HTTP_200_OK,
        )


class VerificationPendingAPIView(APIView):
    """Match Django VerificationPendingView for unverified React members."""

    permission_classes = [permissions.IsAuthenticated]

    def _payload(self, request):
        from accounts.project_access import (
            get_member_project_access_requests,
            get_requestable_projects,
        )

        profile = request.user.profile
        is_verified = bool(profile.is_verified)
        return {
            "isVerified": is_verified,
            "user": {
                "username": request.user.username,
                "firstName": request.user.first_name or "",
                "lastName": request.user.last_name or "",
                "email": request.user.email or "",
                "fullName": profile.display_name,
                "accountNumber": profile.account_number or "Not assigned yet",
                "isVerified": is_verified,
            },
            "requestableProjects": [
                {"id": project.pk, "name": project.name}
                for project in get_requestable_projects(profile)
            ],
            "projectAccessRequests": [
                {
                    "id": f"par-{req.pk}",
                    "project": req.project.name,
                    "status": req.status,
                    "statusDisplay": req.get_status_display(),
                    "createdAt": date_display(req.created_at),
                    "adminNotes": req.admin_notes or "",
                }
                for req in get_member_project_access_requests(profile)[:30]
            ],
            "supportWhatsappUrl": "https://wa.me/256755142271",
            "supportPhone": "+256755142271",
        }

    def get(self, request):
        return Response(self._payload(request))

    def post(self, request):
        from accounts.project_access import (
            build_submission_messages,
            submit_project_access_requests,
        )

        profile = request.user.profile
        if profile.is_verified:
            return Response(
                {"detail": "Your account is already verified.", "isVerified": True},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = request.data or {}
        project_ids = data.get("projectIds") or data.get("project_ids") or []
        member_notes = data.get("memberNotes") or data.get("member_notes") or ""
        if not isinstance(project_ids, (list, tuple)):
            project_ids = [project_ids]

        if not project_ids:
            return Response(
                {"detail": "Select at least one MCS group you belong to."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = submit_project_access_requests(profile, list(project_ids), member_notes)
        messages_out = [
            {"level": level, "text": text}
            for level, text in build_submission_messages(result)
        ]
        payload = self._payload(request)
        payload["messages"] = messages_out
        payload["ok"] = bool(result.get("created"))
        return Response(payload, status=status.HTTP_200_OK)


class MainAccountWithdrawAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _payout_options(self, profile):
        from main_account import services as ledger
        from main_account.models import MainAccountWithdrawal

        mobile = str(profile.whatsapp_number or "").strip()
        bank_name = (profile.bank_name or "").strip()
        bank_account = (profile.bank_account_number or "").strip()
        bank_holder = (profile.bank_account_name or "").strip()
        bank_ready = bool(bank_name and bank_account and bank_holder)
        return {
            "available": money(ledger.available_balance(profile)),
            "pendingWithdrawal": money(ledger.pending_withdrawal_total(profile)),
            "mobileMoney": {
                "method": MainAccountWithdrawal.PAYOUT_MOBILE_MONEY,
                "available": bool(mobile),
                "number": mobile,
                "label": f"Mobile money · {mobile}" if mobile else "Mobile money number not set",
            },
            "bank": {
                "method": MainAccountWithdrawal.PAYOUT_BANK,
                "available": bank_ready,
                "bankName": bank_name,
                "accountNumber": bank_account,
                "accountName": bank_holder,
                "label": (
                    f"{bank_name} · {bank_account} · {bank_holder}"
                    if bank_ready
                    else "Bank account details incomplete"
                ),
            },
        }

    def get(self, request):
        return Response(self._payout_options(request.user.profile))

    def post(self, request):
        from main_account import services as ledger
        from main_account.models import MainAccountWithdrawal

        profile = request.user.profile
        data = request.data or {}
        raw_amount = data.get("amount")
        payout_method = (data.get("payoutMethod") or data.get("payout_method") or "").strip()
        reason = (data.get("reason") or "").strip()

        try:
            amount = Decimal(str(raw_amount).replace(",", "").strip())
        except Exception:
            return Response({"amount": "Enter a valid withdrawal amount."}, status=status.HTTP_400_BAD_REQUEST)

        if payout_method not in {
            MainAccountWithdrawal.PAYOUT_MOBILE_MONEY,
            MainAccountWithdrawal.PAYOUT_BANK,
        }:
            return Response(
                {"payoutMethod": "Choose mobile money or bank account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            withdrawal = ledger.create_withdrawal(
                profile,
                amount,
                reason=reason,
                payout_method=payout_method,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "ok": True,
                "message": "Withdrawal request submitted. It will be reviewed shortly.",
                "withdrawal": {
                    "id": withdrawal.pk,
                    "amount": money(withdrawal.amount),
                    "payoutMethod": withdrawal.payout_method,
                    "payoutDestination": withdrawal.payout_destination,
                    "status": withdrawal.status,
                    "reason": withdrawal.reason or "",
                },
                "mainAccount": {
                    "available": money(ledger.available_balance(profile)),
                    "posted": money(ledger.posted_balance(profile)),
                    "pendingWithdrawal": money(ledger.pending_withdrawal_total(profile)),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class HelpVideosAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        videos = [
            {
                "id": f"hv-{video.pk}",
                "title": video.title,
                "description": video.description,
                "category": video.category,
                "categoryLabel": video.get_category_display(),
                "youtubeId": video.youtube_video_id,
                "embedUrl": video.embed_url,
                "thumbnailUrl": video.thumbnail_url,
            }
            for video in HelpVideo.objects.filter(is_published=True).order_by(
                "category", "sort_order", "-created_at"
            )
        ]
        categories = [{"id": "all", "label": "All"}] + [
            {"id": value, "label": label}
            for value, label in HelpVideo.Category.choices
        ]
        return Response({"categories": categories, "videos": videos})
