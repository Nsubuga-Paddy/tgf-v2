# core/views.py
from django.views import View
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum
from accounts.models import (
    UserProfile,
    WithdrawalRequest,
    GWCContribution,
    MESUInterest,
    ProjectAccessRequest,
)
from accounts.project_access import (
    build_submission_messages,
    get_member_project_access_requests,
    get_requestable_projects,
    submit_project_access_requests,
)
from goat_farming.models import CGFActionRequest
from realestate_projects.models import (
    RealEstateProject,
    RealEstateProjectTransaction,
    RealEstateProjectActionRequest,
)
from accounts.decorators import verified_required
from decimal import Decimal


@method_decorator(login_required, name='dispatch')
@method_decorator(verified_required, name='dispatch')
class LandingPage(TemplateView):
    """
    Landing page that requires user authentication.
    This will be the main dashboard after login.
    """
    template_name = "core/index.html"


class LoginPage(TemplateView):
    """
    Login page template renderer.
    The actual login logic is handled by accounts.views.login_view
    """
    template_name = "core/login.html"


class SignUpPage(TemplateView):
    """
    Signup page template renderer.
    The actual signup logic is handled by accounts.views.signup
    """
    template_name = "core/signup.html"

@method_decorator(login_required, name='dispatch')
class ProfileView(TemplateView):
    template_name = "core/profile.html"

    @staticmethod
    def _has_complete_bank_details(profile):
        return bool(
            profile.bank_name
            and profile.bank_account_number
            and profile.bank_account_name
        )

    @staticmethod
    def _get_missing_dividend_profile_fields(profile):
        missing = []
        if not profile.whatsapp_number:
            missing.append("Phone Number")
        if not profile.national_id:
            missing.append("National ID")
        if not ProfileView._has_complete_bank_details(profile):
            missing.append("Bank Account Details")
        return missing

    def _require_complete_profile_for_coop_dividend(self, request):
        missing = self._get_missing_dividend_profile_fields(request.user.profile)
        if not missing:
            return None
        messages.error(
            request,
            "Please complete your profile before submitting a dividend choice: "
            + ", ".join(missing)
            + ".",
        )
        return redirect("profile")

    def _require_bank_details_for_request(self, request):
        if self._has_complete_bank_details(request.user.profile):
            return None
        messages.error(
            request,
            "Please update your bank account details in your profile before submitting any action request.",
        )
        return redirect("profile")

    @staticmethod
    def _get_realestate_project_balances(user, project):
        txns = RealEstateProjectTransaction.objects.filter(
            project=project,
            user=user,
        )

        gross_amount = Decimal("0")
        for txn in txns:
            if txn.type in (
                RealEstateProjectTransaction.TYPE_PAYMENT,
                RealEstateProjectTransaction.TYPE_ADJUSTMENT,
            ):
                gross_amount += txn.amount
            elif txn.type == RealEstateProjectTransaction.TYPE_REFUND:
                gross_amount -= txn.amount

        pending_withheld = (
            RealEstateProjectActionRequest.objects.filter(
                user=user,
                project=project,
                status=RealEstateProjectActionRequest.STATUS_PENDING,
            ).aggregate(total=Sum("amount"))["total"]
            or Decimal("0")
        )
        approved_deducted = (
            RealEstateProjectActionRequest.objects.filter(
                user=user,
                project=project,
                status__in=[
                    RealEstateProjectActionRequest.STATUS_APPROVED,
                    RealEstateProjectActionRequest.STATUS_PROCESSED,
                ],
            ).aggregate(total=Sum("amount"))["total"]
            or Decimal("0")
        )

        available_amount = gross_amount - pending_withheld - approved_deducted
        if available_amount < 0:
            available_amount = Decimal("0")

        return {
            "gross_amount": gross_amount if gross_amount > 0 else Decimal("0"),
            "withheld_amount": pending_withheld,
            "deducted_amount": approved_deducted,
            "available_amount": available_amount,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get user's accessible projects
        if hasattr(user, 'profile'):
            profile = user.profile
            context['user_projects'] = profile.projects.all()
            context['has_52wsc'] = profile.projects.filter(name='52 Weeks Saving Challenge').exists()
            context['has_cgf'] = profile.projects.filter(name='Commercial Goat Farming').exists()
            context['has_gwc'] = profile.projects.filter(
                name='Generational Wealth Creation'
            ).exists()

            # 52WSC card data: current year saved, interest (unfixed YTD + fixed), available balance (from last year)
            if context['has_52wsc']:
                context['w52_current_year_saved'] = profile.get_current_year_amount_saved()
                context['w52_available_balance'] = profile.get_available_balance()
                try:
                    from savings_52_weeks.interest_utils import calculate_unfixed_interest_ytd
                    unfixed_ytd = calculate_unfixed_interest_ytd(profile)
                    fixed_interest = sum(
                        inv.interest_gained_so_far for inv in profile.investments.all()
                    )
                    context['w52_interest_ytd'] = unfixed_ytd + fixed_interest
                except Exception:
                    context['w52_interest_ytd'] = Decimal('0')
                # Pending requests (withheld) - user can see what they've requested
                context['w52_pending_withdrawals'] = profile.withdrawal_requests.filter(status='pending').order_by('-created_at')
                context['w52_pending_gwc'] = profile.gwc_contributions.filter(status='pending').order_by('-created_at')
                context['w52_pending_mesu'] = profile.mesu_interests.filter(status='pending').order_by('-created_at')
            else:
                context['w52_current_year_saved'] = Decimal('0')
                context['w52_interest_ytd'] = Decimal('0')
                context['w52_available_balance'] = Decimal('0')
                context['w52_pending_withdrawals'] = []
                context['w52_pending_gwc'] = []
                context['w52_pending_mesu'] = []

            # Goat farming data (Commercial Goat Farming)
            if context['has_cgf']:
                try:
                    from goat_farming.models import UserFarmAccount, PackagePurchase
                    from django.db.models import Sum
                    from datetime import timedelta
                    user_farm_accounts = UserFarmAccount.objects.filter(user=profile, is_active=True).select_related('farm')
                    total_goats = user_farm_accounts.aggregate(t=Sum('current_goats'))['t'] or 0
                    context['cgf_total_goats'] = total_goats
                    context['cgf_farms'] = list(user_farm_accounts.values_list('farm__name', flat=True).distinct())
                    context['cgf_total_invested'] = PackagePurchase.objects.filter(user=profile).aggregate(t=Sum('total_amount'))['t'] or Decimal('0')
                    allocated_purchases = PackagePurchase.objects.filter(user=profile, status='allocated').select_related('package')
                    package_based_total = sum(
                        p.goats_allocated * getattr(p.package, 'kids_per_goat', 2)
                        for p in allocated_purchases
                    )
                    effective_kpg = (package_based_total / total_goats) if total_goats else 0
                    context['cgf_expected_kids'] = sum(
                        acc.expected_kids if acc.expected_kids is not None
                        else int(acc.current_goats * effective_kpg)
                        for acc in user_farm_accounts
                    )
                    # Per-farm: total at end of cycle = purchased goats + expected kids (e.g. 2 + 6 = 8)
                    context['cgf_farms_with_goats'] = []
                    total_at_maturity_sum = 0
                    for acc in user_farm_accounts.order_by('farm__name'):
                        resolved_kids = (
                            acc.expected_kids if acc.expected_kids is not None
                            else int(acc.current_goats * effective_kpg)
                        )
                        total_at_maturity = acc.current_goats + resolved_kids
                        total_at_maturity_sum += total_at_maturity
                        context['cgf_farms_with_goats'].append((acc.farm.name, total_at_maturity))
                    context['cgf_total_goats_at_maturity'] = total_at_maturity_sum
                    # Goats already allocated to pending/approved/processed requests (exclude rejected)
                    allocated_to_requests = CGFActionRequest.objects.filter(
                        user_profile=profile
                    ).exclude(status='rejected').exclude(goats_count__isnull=True).aggregate(
                        total=Sum('goats_count')
                    )['total'] or 0
                    context['cgf_goats_available'] = max(0, total_at_maturity_sum - int(allocated_to_requests))
                    context['cgf_goat_sell_price'] = 400000  # UGX per goat when cashing out
                    now = timezone.now()
                    cutoff = now - timedelta(days=425)
                    context['cgf_has_completed_cycles'] = PackagePurchase.objects.filter(
                        user=profile, status='allocated', purchase_date__lte=cutoff
                    ).exists()
                    # User's CGF action requests (Sell, Take, Transfer) for display
                    context['cgf_action_requests'] = profile.cgf_action_requests.all().order_by('-created_at')
                except Exception:
                    context['cgf_total_goats'] = 0
                    context['cgf_farms'] = []
                    context['cgf_total_invested'] = Decimal('0')
                    context['cgf_expected_kids'] = 0
                    context['cgf_farms_with_goats'] = []
                    context['cgf_total_goats_at_maturity'] = 0
                    context['cgf_goats_available'] = 0
                    context['cgf_goat_sell_price'] = 400000
                    context['cgf_has_completed_cycles'] = False
                    context['cgf_action_requests'] = []
            else:
                context['cgf_total_goats'] = 0
                context['cgf_farms'] = []
                context['cgf_total_invested'] = Decimal('0')
                context['cgf_expected_kids'] = 0
                context['cgf_farms_with_goats'] = []
                context['cgf_total_goats_at_maturity'] = 0
                context['cgf_goats_available'] = 0
                context['cgf_goat_sell_price'] = 400000
                context['cgf_has_completed_cycles'] = False
                context['cgf_action_requests'] = []

            # Share holding summary (MESU interests)
            from django.db.models import Sum

            approved_mesu = profile.mesu_interests.filter(
                status__in=["approved", "processed"]
            )
            context["mesu_interests"] = profile.mesu_interests.all().order_by(
                "-created_at"
            )
            context["mesu_total_shares"] = sum(
                m.number_of_shares or 0 for m in approved_mesu
            )
            mesu_agg = approved_mesu.aggregate(total=Sum("investment_amount"))
            context["mesu_total_invested"] = mesu_agg["total"] or Decimal("0")

            # Cooperative shareholding (SACCO — separate from MESU Academy)
            from cooperative_shareholding.models import (
                CooperativeShareholding,
                DividendChoiceRequest,
            )
            from cooperative_shareholding.services import (
                build_dividend_account_summary,
                build_pending_edit_payload,
                build_shareholding_summary,
                cooperative_display_state,
                user_has_cooperative_access,
            )

            context["has_cooperative_access"] = user_has_cooperative_access(profile)
            coop_holding = None
            try:
                coop_holding = user.cooperative_shareholding
            except CooperativeShareholding.DoesNotExist:
                pass
            context["cooperative_shareholding"] = coop_holding
            context["show_cooperative_section"] = True
            context["coop_display_state"] = cooperative_display_state(
                profile, coop_holding
            )
            if coop_holding and context["coop_display_state"] == "full":
                context["coop_summary"] = build_shareholding_summary(coop_holding)
                context["coop_dividend_account"] = build_dividend_account_summary(
                    coop_holding
                )
                context["coop_acquisition_lines"] = coop_holding.acquisition_lines.filter(
                    shares_held__gt=0
                )
                context["coop_pending_submission"] = (
                    DividendChoiceRequest.objects.filter(
                        shareholding=coop_holding,
                        status=DividendChoiceRequest.Status.PENDING,
                    )
                    .prefetch_related("allocation_lines")
                    .first()
                )
                context["coop_pending_dividend_choice"] = context[
                    "coop_pending_submission"
                ]
                context["coop_submitted_dividend_choice"] = (
                    DividendChoiceRequest.objects.filter(shareholding=coop_holding)
                    .exclude(status=DividendChoiceRequest.Status.REJECTED)
                    .prefetch_related("allocation_lines")
                    .order_by("-created_at")
                    .first()
                )
                context["coop_election_open"] = coop_holding.dividend_election_open
                locked_statuses = (
                    DividendChoiceRequest.Status.APPROVED,
                    DividendChoiceRequest.Status.PROCESSED,
                )
                context["coop_dividend_locked"] = (
                    DividendChoiceRequest.objects.filter(
                        shareholding=coop_holding,
                        status__in=locked_statuses,
                    ).exists()
                )
                coop_missing_profile = self._get_missing_dividend_profile_fields(
                    profile
                )
                coop_profile_complete = not coop_missing_profile
                context["coop_missing_profile_fields"] = coop_missing_profile
                context["coop_profile_blocks_dividend"] = not coop_profile_complete
                context["coop_needs_personal_info"] = (
                    "Phone Number" in coop_missing_profile
                    or "National ID" in coop_missing_profile
                )
                context["coop_needs_bank_details"] = (
                    "Bank Account Details" in coop_missing_profile
                )
                context["coop_can_edit_dividend"] = bool(
                    context["coop_pending_submission"]
                ) and coop_profile_complete
                context["coop_show_dividend_choices"] = (
                    context["coop_election_open"]
                    and not context["coop_dividend_locked"]
                    and not context["coop_pending_submission"]
                    and coop_profile_complete
                )
                pending = context["coop_pending_submission"]
                context["coop_edit_payload"] = (
                    build_pending_edit_payload(pending) if pending else None
                )
            else:
                context["coop_summary"] = None
                context["coop_dividend_account"] = None
                context["coop_acquisition_lines"] = []
                context["coop_pending_submission"] = None
                context["coop_pending_dividend_choice"] = None
                context["coop_submitted_dividend_choice"] = None
                context["coop_dividend_locked"] = False
                context["coop_can_edit_dividend"] = False
                context["coop_show_dividend_choices"] = False
                context["coop_edit_payload"] = None
                context["coop_election_open"] = False
                context["coop_missing_profile_fields"] = []
                context["coop_profile_blocks_dividend"] = False
                context["coop_needs_personal_info"] = False
                context["coop_needs_bank_details"] = False

            # Real estate projects visible to user by admin access (allowed_members)
            # No manual membership creation required for profile actions.
            realestate_projects = RealEstateProject.objects.filter(
                allowed_members=user
            ).distinct().order_by("name")
            realestate_projects_data = []
            for project in realestate_projects:
                balances = self._get_realestate_project_balances(user, project)
                realestate_projects_data.append(
                    {
                        "project": project,
                        **balances,
                    }
                )
            context["realestate_projects_data"] = realestate_projects_data

            # GWC fixed deposits (Generational Wealth Creation project)
            if context["has_gwc"]:
                try:
                    from gwc.models import GWCFixedDeposit
                    from gwc.services import portfolio_summary_for_user

                    context["gwc_portfolio"] = portfolio_summary_for_user(user)
                    context["gwc_deposits_count"] = GWCFixedDeposit.objects.filter(
                        user=user
                    ).count()
                    context["gwc_active_count"] = GWCFixedDeposit.objects.filter(
                        user=user, status=GWCFixedDeposit.Status.ACTIVE
                    ).count()
                    next_mat = (
                        GWCFixedDeposit.objects.filter(
                            user=user,
                            status=GWCFixedDeposit.Status.ACTIVE,
                        )
                        .order_by("maturity_date")
                        .values_list("maturity_date", flat=True)
                        .first()
                    )
                    context["gwc_nearest_maturity_date"] = next_mat
                except Exception:
                    context["gwc_portfolio"] = {
                        "total_principal": Decimal("0"),
                        "total_accrued_interest": Decimal("0"),
                        "total_maturity_value": Decimal("0"),
                    }
                    context["gwc_deposits_count"] = 0
                    context["gwc_active_count"] = 0
                    context["gwc_nearest_maturity_date"] = None
            else:
                context["gwc_portfolio"] = {
                    "total_principal": Decimal("0"),
                    "total_accrued_interest": Decimal("0"),
                    "total_maturity_value": Decimal("0"),
                }
                context["gwc_deposits_count"] = 0
                context["gwc_active_count"] = 0
                context["gwc_nearest_maturity_date"] = None

            # Unified action requests from all projects (for Action Requests panel)
            all_requests = []
            for r in profile.withdrawal_requests.all().order_by('-created_at'):
                all_requests.append({
                    'project': '52WSC',
                    'type_label': 'Withdrawal',
                    'icon': 'fa-money-bill-wave',
                    'detail': f"UGX {r.amount:,.0f}",
                    'status': r.status,
                    'status_display': r.get_status_display(),
                    'created_at': r.created_at,
                })
            for r in profile.gwc_contributions.all().order_by('-created_at'):
                all_requests.append({
                    'project': '52WSC',
                    'type_label': 'Transfer to GWC',
                    'icon': 'fa-users',
                    'detail': f"UGX {r.amount:,.0f}",
                    'status': r.status,
                    'status_display': r.get_status_display(),
                    'created_at': r.created_at,
                })
            for r in profile.mesu_interests.all().order_by('-created_at'):
                all_requests.append({
                    'project': '52WSC',
                    'type_label': 'MESU Shares',
                    'icon': 'fa-graduation-cap',
                    'detail': f"{r.number_of_shares} share(s) · UGX {r.investment_amount:,.0f}",
                    'status': r.status,
                    'status_display': r.get_status_display(),
                    'created_at': r.created_at,
                })
            for r in profile.project_access_requests.select_related("project").order_by(
                "-created_at"
            ):
                detail = r.project.name
                if r.member_notes:
                    detail += f" · {r.member_notes[:80]}"
                if r.status == ProjectAccessRequest.STATUS_REJECTED and r.admin_notes:
                    detail += f" · Reason: {r.admin_notes}"
                all_requests.append({
                    "project": "Platform",
                    "type_label": "Project access",
                    "icon": "fa-door-open",
                    "detail": detail,
                    "status": r.status,
                    "status_display": r.get_status_display(),
                    "created_at": r.created_at,
                })
            for r in profile.cgf_action_requests.all().order_by('-created_at'):
                detail = f"{r.goats_count or 0} goats"
                if r.request_type == 'sell_cash_out':
                    detail += f" · UGX {r.cash_value:,.0f}"
                type_map = {'sell_cash_out': 'Sell & Cash Out', 'take_goats': 'Take Goats', 'transfer': 'Transfer'}
                icon_map = {'sell_cash_out': 'fa-hand-holding-usd', 'take_goats': 'fa-truck-loading', 'transfer': 'fa-exchange-alt'}
                all_requests.append({
                    'project': 'CGF',
                    'type_label': type_map.get(r.request_type, r.request_type),
                    'icon': icon_map.get(r.request_type, 'fa-tasks'),
                    'detail': detail,
                    'status': r.status,
                    'status_display': r.get_status_display(),
                    'created_at': r.created_at,
                })
            # Real estate project action requests
            for r in profile.user.realestate_action_requests.all().order_by('-created_at'):
                type_map = {
                    RealEstateProjectActionRequest.ACTION_WITHDRAW: 'Withdraw from Real Estate',
                    RealEstateProjectActionRequest.ACTION_TRANSFER_GWC: 'Transfer to GWC',
                    RealEstateProjectActionRequest.ACTION_TRANSFER_NAMAYUMBA: 'Transfer to Namayumba estate',
                }
                icon_map = {
                    RealEstateProjectActionRequest.ACTION_WITHDRAW: 'fa-money-bill-wave',
                    RealEstateProjectActionRequest.ACTION_TRANSFER_GWC: 'fa-users',
                    RealEstateProjectActionRequest.ACTION_TRANSFER_NAMAYUMBA: 'fa-building',
                }
                all_requests.append({
                    'project': 'Real Estate',
                    'type_label': type_map.get(r.action_type, r.action_type),
                    'icon': icon_map.get(r.action_type, 'fa-tasks'),
                    'detail': f"{r.project.name} · UGX {r.amount:,.0f}",
                    'status': r.status,
                    'status_display': r.get_status_display(),
                    'created_at': r.created_at,
                })
            if coop_holding:
                from cooperative_shareholding.models import DividendAllocationLine

                coop_icons = {
                    DividendAllocationLine.ActionType.CASH: "fa-money-bill-wave",
                    DividendAllocationLine.ActionType.MCS_SHARES: "fa-chart-line",
                    DividendAllocationLine.ActionType.MESU_SHARES: "fa-graduation-cap",
                    DividendAllocationLine.ActionType.SAVINGS: "fa-piggy-bank",
                }
                for sub in coop_holding.dividend_choices.prefetch_related(
                    "allocation_lines"
                ).order_by("-created_at"):
                    for line in sub.allocation_lines.all():
                        all_requests.append({
                            "project": "Cooperative",
                            "type_label": (
                                f"Dividend — {line.get_action_type_display()}"
                            ),
                            "icon": coop_icons.get(line.action_type, "fa-landmark"),
                            "detail": f"UGX {line.amount:,.0f}",
                            "status": sub.status,
                            "status_display": sub.get_status_display(),
                            "created_at": sub.created_at,
                        })
            def _sort_key(item):
                dt = item['created_at']
                return dt if timezone.is_aware(dt) else timezone.make_aware(dt)
            all_requests.sort(key=_sort_key, reverse=True)
            context['all_action_requests'] = all_requests

            missing_fields = self._get_missing_dividend_profile_fields(profile)
            context['missing_fields'] = missing_fields
            context['has_missing_fields'] = len(missing_fields) > 0
            context['requestable_projects'] = (
                get_requestable_projects(profile) if profile.is_verified else []
            )
            context['project_access_requests'] = get_member_project_access_requests(profile)
            context['granted_project_names'] = list(
                profile.projects.values_list("name", flat=True)
            )
        else:
            context['user_projects'] = []
            context['has_52wsc'] = False
            context['has_cgf'] = False
            context['has_gwc'] = False
            context['w52_current_year_saved'] = Decimal('0')
            context['w52_interest_ytd'] = Decimal('0')
            context['w52_available_balance'] = Decimal('0')
            context['w52_pending_withdrawals'] = []
            context['w52_pending_gwc'] = []
            context['w52_pending_mesu'] = []
            context['cgf_total_goats'] = 0
            context['cgf_farms'] = []
            context['cgf_total_invested'] = Decimal('0')
            context['cgf_expected_kids'] = 0
            context['cgf_farms_with_goats'] = []
            context['cgf_total_goats_at_maturity'] = 0
            context['cgf_goats_available'] = 0
            context['cgf_goat_sell_price'] = 400000
            context['cgf_has_completed_cycles'] = False
            context['cgf_action_requests'] = []
            context['all_action_requests'] = []
            context['mesu_interests'] = []
            context['mesu_total_shares'] = 0
            context['mesu_total_invested'] = Decimal('0')
            context['has_cooperative_access'] = False
            context['show_cooperative_section'] = True
            context['coop_display_state'] = 'no_access'
            context['cooperative_shareholding'] = None
            context['coop_summary'] = None
            context['coop_dividend_account'] = None
            context['coop_acquisition_lines'] = []
            context['coop_election_open'] = False
            context['coop_pending_submission'] = None
            context['coop_pending_dividend_choice'] = None
            context['coop_submitted_dividend_choice'] = None
            context['coop_dividend_locked'] = False
            context['coop_can_edit_dividend'] = False
            context['coop_show_dividend_choices'] = False
            context['coop_edit_payload'] = None
            context['realestate_projects_data'] = []
            context['gwc_portfolio'] = {
                "total_principal": Decimal("0"),
                "total_accrued_interest": Decimal("0"),
                "total_maturity_value": Decimal("0"),
            }
            context["gwc_deposits_count"] = 0
            context["gwc_active_count"] = 0
            context["gwc_nearest_maturity_date"] = None
            context['missing_fields'] = []
            context['has_missing_fields'] = False
            context['requestable_projects'] = []
            context['project_access_requests'] = []
            context['granted_project_names'] = []
            
        context['user'] = user
        return context
    
    def post(self, request, *args, **kwargs):
        user = request.user
        action = request.POST.get('action')
        
        # Handle different actions
        if action == 'withdraw':
            return self.handle_withdraw(request)
        elif action == 'join_gwc':
            return self.handle_join_gwc(request)
        elif action == 'buy_mesu':
            return self.handle_buy_mesu(request)
        elif action == 'cgf_sell_cash_out':
            return self.handle_cgf_action(request, 'sell_cash_out')
        elif action == 'cgf_take_goats':
            return self.handle_cgf_action(request, 'take_goats')
        elif action == 'cgf_transfer':
            return self.handle_cgf_action(request, 'transfer')
        elif action == 'rep_withdraw':
            return self.handle_realestate_action(request, RealEstateProjectActionRequest.ACTION_WITHDRAW)
        elif action == 'rep_transfer_gwc':
            return self.handle_realestate_action(request, RealEstateProjectActionRequest.ACTION_TRANSFER_GWC)
        elif action == 'rep_transfer_namayumba':
            return self.handle_realestate_action(request, RealEstateProjectActionRequest.ACTION_TRANSFER_NAMAYUMBA)
        elif action == 'cooperative_dividend_choice':
            return self.handle_cooperative_dividend_choice(request)
        elif action == 'request_project_access':
            return self.handle_request_project_access(request)

        # Default: Update profile information
        # Update User model fields
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.save()
        
        # Update UserProfile fields
        profile = user.profile
        
        # Validate WhatsApp number (required)
        whatsapp_number = request.POST.get('whatsapp_number', '').strip()
        if not whatsapp_number:
            messages.error(request, 'WhatsApp number is required. Please provide your phone number for contact purposes.')
            return redirect('profile')
        
        profile.whatsapp_number = whatsapp_number
        profile.national_id = request.POST.get('national_id', '')
        profile.address = request.POST.get('address', '')
        profile.bio = request.POST.get('bio', '')
        
        # Handle bank account information
        profile.bank_name = request.POST.get('bank_name', '').strip() or None
        profile.bank_account_number = request.POST.get('bank_account_number', '').strip() or None
        profile.bank_account_name = request.POST.get('bank_account_name', '').strip() or None
        
        # Handle birthdate
        birthdate = request.POST.get('birthdate')
        if birthdate:
            profile.birthdate = birthdate
        else:
            profile.birthdate = None
        
        # Handle profile photo upload
        if 'photo' in request.FILES:
            profile.photo = request.FILES['photo']
        
        profile.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')
    
    def handle_request_project_access(self, request):
        profile = request.user.profile
        if not profile.is_verified:
            messages.error(
                request,
                "Complete account verification first, or submit group requests on the verification pending page.",
            )
            return redirect("verification_pending")

        project_ids = request.POST.getlist("project_ids")
        member_notes = request.POST.get("member_notes", "")
        if not project_ids:
            messages.warning(request, "Select at least one project to request access.")
            return redirect("profile")

        result = submit_project_access_requests(profile, project_ids, member_notes)
        for level, msg in build_submission_messages(result):
            getattr(messages, level)(request, msg)
        return redirect("profile")

    def handle_withdraw(self, request):
        """Handle withdrawal request"""
        user = request.user
        profile = user.profile

        bank_guard = self._require_bank_details_for_request(request)
        if bank_guard:
            return bank_guard
        
        try:
            withdraw_amount = Decimal(request.POST.get('withdraw_amount', '0'))
            available_balance = profile.get_available_balance()
            
            if withdraw_amount < 1000:
                messages.error(request, 'Minimum withdrawal amount is UGX 1,000.')
                return redirect('profile')
            
            if withdraw_amount > available_balance:
                messages.error(request, 'Insufficient balance. Available: UGX {:,}'.format(int(available_balance)))
                return redirect('profile')
            
            # Create withdrawal request record
            WithdrawalRequest.objects.create(
                user_profile=profile,
                amount=withdraw_amount,
                reason=request.POST.get('withdraw_reason', ''),
                status='pending'
            )
            
            # Redirect with success parameter for enhanced notification
            return redirect(f"{reverse('profile')}?action=withdraw_success&amount={withdraw_amount:,.0f}")
            
        except (ValueError, TypeError) as e:
            messages.error(request, 'Invalid withdrawal amount.')
            return redirect('profile')
        
        return redirect('profile')
    
    def handle_join_gwc(self, request):
        """Handle GWC group join request"""
        user = request.user
        profile = user.profile

        bank_guard = self._require_bank_details_for_request(request)
        if bank_guard:
            return bank_guard
        
        try:
            gwc_amount = Decimal(request.POST.get('gwc_amount', '0'))
            group_type = request.POST.get('gwc_group_type', '')
            available_balance = profile.get_available_balance()
            
            if gwc_amount < 1000:
                messages.error(request, 'Minimum contribution amount is UGX 1,000.')
                return redirect('profile')
            
            if gwc_amount > available_balance:
                messages.error(request, 'Insufficient balance. Available: UGX {:,}'.format(int(available_balance)))
                return redirect('profile')
            
            if not group_type:
                messages.error(request, 'Please select a group type.')
                return redirect('profile')
            
            # Create GWC contribution record
            GWCContribution.objects.create(
                user_profile=profile,
                amount=gwc_amount,
                group_type=group_type,
                status='pending'
            )
            
            # Redirect with success parameter for enhanced notification
            return redirect(f"{reverse('profile')}?action=gwc_success&amount={gwc_amount:,.0f}&type={group_type}")
            
        except (ValueError, TypeError) as e:
            messages.error(request, 'Invalid contribution amount.')
            return redirect('profile')
        
        return redirect('profile')
    
    def handle_buy_mesu(self, request):
        """Handle MESU shares purchase request"""
        user = request.user
        profile = user.profile

        bank_guard = self._require_bank_details_for_request(request)
        if bank_guard:
            return bank_guard
        
        try:
            mesu_amount = Decimal(request.POST.get('mesu_amount', '0'))
            total_savings = profile.get_total_savings()
            
            if mesu_amount < 1000000:
                messages.error(request, 'Minimum investment amount is UGX 1,000,000 (1 share).')
                return redirect('profile')
            
            if mesu_amount > total_savings:
                messages.error(request, 'Insufficient balance. Available: UGX {:,}'.format(int(total_savings)))
                return redirect('profile')
            
            # Calculate number of shares (1 share = 1,000,000 UGX)
            number_of_shares = int(mesu_amount / Decimal('1000000'))
            
            # Create MESU interest record
            MESUInterest.objects.create(
                user_profile=profile,
                investment_amount=mesu_amount,
                number_of_shares=number_of_shares,
                notes=request.POST.get('mesu_notes', ''),
                status='pending'
            )
            
            # Redirect with success parameter for enhanced notification
            return redirect(f"{reverse('profile')}?action=mesu_success&shares={number_of_shares}&amount={mesu_amount:,.0f}")
            
        except (ValueError, TypeError) as e:
            messages.error(request, 'Invalid investment amount.')
            return redirect('profile')
        
        return redirect('profile')

    def handle_cgf_action(self, request, request_type):
        """Handle CGF action request (Sell & Cash Out, Take Goats, Transfer)"""
        user = request.user
        profile = user.profile

        bank_guard = self._require_bank_details_for_request(request)
        if bank_guard:
            return bank_guard

        # Verify user has CGF project
        from accounts.models import Project
        from goat_farming.models import UserFarmAccount, PackagePurchase
        from django.db.models import Sum
        cgf = Project.objects.filter(name='Commercial Goat Farming', members=profile).first()
        if not cgf:
            messages.error(request, 'You do not have access to Commercial Goat Farming.')
            return redirect('profile')

        # Get goats_count from form
        try:
            goats_count = int(request.POST.get('cgf_goats_count', 0) or 0)
        except (ValueError, TypeError):
            goats_count = 0

        if goats_count < 1:
            messages.error(request, 'Please enter the number of goats (at least 1).')
            return redirect('profile')

        # Compute total at maturity and available goats (same logic as get_context_data)
        user_farm_accounts = UserFarmAccount.objects.filter(user=profile, is_active=True).select_related('farm')
        total_goats = user_farm_accounts.aggregate(t=Sum('current_goats'))['t'] or 0
        allocated_purchases = PackagePurchase.objects.filter(user=profile, status='allocated').select_related('package')
        package_based_total = sum(
            p.goats_allocated * getattr(p.package, 'kids_per_goat', 2)
            for p in allocated_purchases
        )
        effective_kpg = (package_based_total / total_goats) if total_goats else 0
        total_at_maturity = 0
        for acc in user_farm_accounts:
            resolved_kids = (
                acc.expected_kids if acc.expected_kids is not None
                else int(acc.current_goats * effective_kpg)
            )
            total_at_maturity += acc.current_goats + resolved_kids
        allocated_to_requests = CGFActionRequest.objects.filter(
            user_profile=profile
        ).exclude(status='rejected').exclude(goats_count__isnull=True).aggregate(
            total=Sum('goats_count')
        )['total'] or 0
        goats_available = max(0, total_at_maturity - int(allocated_to_requests))

        if goats_count > goats_available:
            messages.error(
                request,
                f'You have only {goats_available} goat(s) available. You have pending requests that reduce the remaining count.'
            )
            return redirect('profile')

        CGFActionRequest.objects.create(
            user_profile=profile,
            request_type=request_type,
            goats_count=goats_count,
            notes=request.POST.get('cgf_notes', ''),
            status='pending'
        )

        return redirect(f"{reverse('profile')}?action=cgf_request_success&type={request_type}")

    def handle_realestate_action(self, request, action_type):
        """Handle real estate project action requests (withdraw, transfer to GWC/Namayumba)."""
        user = request.user

        bank_guard = self._require_bank_details_for_request(request)
        if bank_guard:
            return bank_guard

        try:
            project_id = int(request.POST.get("rep_project_id", "0") or 0)
        except (ValueError, TypeError):
            project_id = 0

        if project_id <= 0:
            messages.error(request, "Invalid project selection.")
            return redirect("profile")

        project = RealEstateProject.objects.filter(
            id=project_id,
            allowed_members=user,
        ).first()
        if not project:
            messages.error(request, "You do not have access to the selected real estate project.")
            return redirect("profile")

        # Amount to act on
        try:
            amount = Decimal(request.POST.get("rep_amount", "0") or "0")
        except (ValueError, TypeError):
            messages.error(request, "Invalid amount.")
            return redirect("profile")

        if amount <= 0:
            messages.error(request, "Please enter a positive amount.")
            return redirect("profile")

        balances = self._get_realestate_project_balances(user, project)
        available = balances["available_amount"]
        if amount > available:
            messages.error(
                request,
                f"Requested amount exceeds your available amount for this project (max UGX {available:,.0f}).",
            )
            return redirect("profile")

        RealEstateProjectActionRequest.objects.create(
            user=user,
            project=project,
            action_type=action_type,
            amount=amount,
            available_at_request=available,
            reason=request.POST.get("rep_notes", ""),
            status=RealEstateProjectActionRequest.STATUS_PENDING,
        )

        return redirect(f"{reverse('profile')}?action=rep_request_success&type={action_type}")

    def handle_cooperative_dividend_choice(self, request):
        """Create or update cooperative dividend allocation (pending only)."""
        from cooperative_shareholding.models import (
            CooperativeShareholding,
            DividendAllocationLine,
            DividendChoiceRequest,
        )
        from cooperative_shareholding.services import (
            build_shareholding_summary,
            create_dividend_submission,
            parse_dividend_allocations_from_post,
            submission_is_editable_by_member,
            update_dividend_submission,
            user_has_cooperative_access,
            validate_dividend_allocations,
        )

        user = request.user
        profile = user.profile
        if not user_has_cooperative_access(profile):
            messages.error(request, "You do not have access to Cooperative Shareholding.")
            return redirect("profile")

        profile_guard = self._require_complete_profile_for_coop_dividend(request)
        if profile_guard:
            return profile_guard

        try:
            shareholding = user.cooperative_shareholding
        except CooperativeShareholding.DoesNotExist:
            messages.error(
                request,
                "Your cooperative shareholding record has not been set up yet. Contact the office.",
            )
            return redirect("profile")

        locked_statuses = (
            DividendChoiceRequest.Status.APPROVED,
            DividendChoiceRequest.Status.PROCESSED,
        )
        submission_id = request.POST.get("coop_submission_id", "").strip()
        existing_submission = None
        is_update = False
        if submission_id:
            is_update = True
            try:
                existing_submission = DividendChoiceRequest.objects.prefetch_related(
                    "allocation_lines"
                ).get(
                    pk=int(submission_id),
                    shareholding=shareholding,
                )
            except (DividendChoiceRequest.DoesNotExist, ValueError, TypeError):
                messages.error(request, "Invalid dividend request.")
                return redirect("profile")
            if not submission_is_editable_by_member(existing_submission):
                messages.error(
                    request,
                    "This dividend request has been approved and can no longer be edited.",
                )
                return redirect("profile")
        elif not is_update and not shareholding.dividend_election_open:
            messages.error(request, "Dividend election is not open for your account.")
            return redirect("profile")
        elif not is_update and DividendChoiceRequest.objects.filter(
            shareholding=shareholding,
            status__in=locked_statuses,
        ).exists():
            messages.error(
                request,
                "Your dividend request has been approved and can no longer be changed.",
            )
            return redirect("profile")
        elif DividendChoiceRequest.objects.filter(
            shareholding=shareholding,
            status=DividendChoiceRequest.Status.PENDING,
        ).exists():
            messages.error(
                request,
                "You already have a pending dividend request. Use Edit to update it.",
            )
            return redirect("profile")
        elif not is_update and (
            DividendChoiceRequest.objects.filter(shareholding=shareholding)
            .exclude(status=DividendChoiceRequest.Status.REJECTED)
            .exists()
        ):
            messages.error(request, "You have already submitted a dividend choice.")
            return redirect("profile")

        summary = build_shareholding_summary(shareholding)
        expected_total = summary["expected_dividend"]
        valid_types = {c[0] for c in DividendAllocationLine.ActionType.choices}
        single_type = request.POST.get("coop_action_type", "").strip()
        if single_type == "more_shares":
            single_type = DividendAllocationLine.ActionType.MCS_SHARES

        if single_type:
            if single_type not in valid_types:
                messages.error(request, "Invalid dividend choice.")
                return redirect("profile")
            allocations = [(single_type, expected_total)]
            success_type = single_type
        else:
            allocations = parse_dividend_allocations_from_post(request.POST)
            error = validate_dividend_allocations(allocations, expected_total)
            if error:
                messages.error(request, error)
                return redirect("profile")
            success_type = "split"

        member_notes = request.POST.get("coop_notes", "")
        if existing_submission:
            update_dividend_submission(
                existing_submission,
                expected_total,
                allocations,
                member_notes=member_notes,
            )
            messages.success(
                request,
                "Your pending dividend allocation has been updated.",
            )
            success_type = "updated"
        else:
            create_dividend_submission(
                shareholding,
                expected_total,
                allocations,
                member_notes=member_notes,
            )
            messages.success(
                request,
                "Your dividend allocation has been submitted. Track status under Action Requests.",
            )
        return redirect(
            f"{reverse('profile')}?action=coop_dividend_success&type={success_type}"
        )


@method_decorator(login_required, name="dispatch")
class VerificationPendingView(View):
    """Page for unverified members — includes TGF group access requests."""

    template_name = "core/verification_pending.html"

    def dispatch(self, request, *args, **kwargs):
        if (
            request.user.is_authenticated
            and hasattr(request.user, "profile")
            and request.user.profile.is_verified
        ):
            return redirect("landing")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        return self._render(request)

    def post(self, request):
        if request.POST.get("action") != "submit_project_access":
            return self._render(request)

        profile = request.user.profile
        project_ids = request.POST.getlist("project_ids")
        member_notes = request.POST.get("member_notes", "")

        if not project_ids:
            messages.warning(request, "Select at least one MCS group you belong to.")
            return redirect("verification_pending")

        result = submit_project_access_requests(profile, project_ids, member_notes)
        for level, msg in build_submission_messages(result):
            getattr(messages, level)(request, msg)
        return redirect("verification_pending")

    def _render(self, request):
        profile = request.user.profile
        context = {
            "user": request.user,
            "requestable_projects": get_requestable_projects(profile),
            "project_access_requests": get_member_project_access_requests(profile),
            "granted_project_names": list(profile.projects.values_list("name", flat=True)),
        }
        return render(request, self.template_name, context)







