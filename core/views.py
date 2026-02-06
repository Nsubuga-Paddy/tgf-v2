# core/views.py
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.models import User
from django.utils import timezone
from accounts.models import UserProfile, WithdrawalRequest, GWCContribution, MESUInterest
from goat_farming.models import CGFActionRequest
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
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get user's accessible projects
        if hasattr(user, 'profile'):
            profile = user.profile
            context['user_projects'] = profile.projects.all()
            context['has_52wsc'] = profile.projects.filter(name='52 Weeks Saving Challenge').exists()
            context['has_cgf'] = profile.projects.filter(name='Commercial Goat Farming').exists()

            # 52WSC card data: current year saved, daily interest YTD, available balance (from last year)
            if context['has_52wsc']:
                context['w52_current_year_saved'] = profile.get_current_year_amount_saved()
                context['w52_available_balance'] = profile.get_available_balance()
                try:
                    from savings_52_weeks.interest_utils import calculate_unfixed_interest_ytd
                    context['w52_interest_ytd'] = calculate_unfixed_interest_ytd(profile)
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
                    from django.utils import timezone
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

            # Share holding summary (MESU interests) (MESU interests)
            from django.db.models import Sum
            approved_mesu = profile.mesu_interests.filter(status__in=['approved', 'processed'])
            context['mesu_interests'] = profile.mesu_interests.all().order_by('-created_at')
            context['mesu_total_shares'] = sum(m.number_of_shares or 0 for m in approved_mesu)
            mesu_agg = approved_mesu.aggregate(total=Sum('investment_amount'))
            context['mesu_total_invested'] = mesu_agg['total'] or Decimal('0')

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
                    'type_label': f'GWC ({r.get_group_type_display()})',
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
            def _sort_key(item):
                dt = item['created_at']
                return dt if timezone.is_aware(dt) else timezone.make_aware(dt)
            all_requests.sort(key=_sort_key, reverse=True)
            context['all_action_requests'] = all_requests

            # Check for missing required information
            missing_fields = []
            if not profile.whatsapp_number:
                missing_fields.append('Phone Number')
            if not profile.national_id:
                missing_fields.append('National ID')
            if not profile.bank_name or not profile.bank_account_number or not profile.bank_account_name:
                missing_fields.append('Bank Account Details')

            context['missing_fields'] = missing_fields
            context['has_missing_fields'] = len(missing_fields) > 0
        else:
            context['user_projects'] = []
            context['has_52wsc'] = False
            context['has_cgf'] = False
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
            context['missing_fields'] = []
            context['has_missing_fields'] = False
            
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
    
    def handle_withdraw(self, request):
        """Handle withdrawal request"""
        user = request.user
        profile = user.profile
        
        # Check if bank details are provided
        if not profile.bank_name or not profile.bank_account_number or not profile.bank_account_name:
            messages.error(request, 'Please update your bank account details in your profile before requesting a withdrawal.')
            return redirect('profile')
        
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


class VerificationPendingView(TemplateView):
    """
    Page shown to users whose accounts are awaiting verification.
    """
    template_name = "core/verification_pending.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context







