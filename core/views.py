# core/views.py
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.models import User
from accounts.models import UserProfile, WithdrawalRequest, GWCContribution, MESUInterest
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
            context['user_projects'] = user.profile.projects.all()
            profile = user.profile
            
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


class VerificationPendingView(TemplateView):
    """
    Page shown to users whose accounts are awaiting verification.
    """
    template_name = "core/verification_pending.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context







