# core/views.py
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction as db_transaction
from django.utils import timezone
from decimal import Decimal
from accounts.models import UserProfile, WithdrawalRequest, MESUInterest
from accounts.decorators import verified_required


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
        from decimal import Decimal
        
        # Get user's accessible projects
        if hasattr(user, 'profile'):
            user_profile = user.profile
            context['user_projects'] = user_profile.projects.all()
            
            # Calculate total savings including matured interest (from 52WSC)
            total_savings = Decimal('0.00')
            project_breakdown = []
            
            # Get 52WSC savings if user has access
            if user_profile.projects.filter(name='52 Weeks Saving Challenge').exists():
                try:
                    from savings_52_weeks.models import SavingsTransaction
                    # Process interest payments first
                    from savings_52_weeks.utils import process_user_interest_payments
                    process_user_interest_payments(user_profile)
                    
                    # Get total savings (includes all deposits including interest)
                    savings_52wsc = SavingsTransaction.get_user_total_savings(user_profile)
                    total_savings += savings_52wsc
                    
                    # Get invested amount in 52WSC
                    invested_52wsc = sum(
                        inv.amount_invested for inv in user_profile.investments.filter(status='fixed')
                    )
                    
                    project_breakdown.append({
                        'name': '52 Weeks Saving Challenge',
                        'total_savings': savings_52wsc,
                        'invested': invested_52wsc,
                        'available': savings_52wsc - invested_52wsc,
                    })
                except Exception as e:
                    print(f"Error calculating 52WSC savings: {e}")
            
            # Add other projects here as they're implemented
            # For now, we'll show 52WSC breakdown
            
            # Calculate total available (not invested in any project)
            total_invested = sum(p['invested'] for p in project_breakdown)
            total_available = total_savings - total_invested
            
            context['total_savings'] = total_savings
            context['total_available'] = total_available
            context['project_breakdown'] = project_breakdown
        else:
            context['user_projects'] = []
            context['total_savings'] = Decimal('0.00')
            context['total_available'] = Decimal('0.00')
            context['project_breakdown'] = []
            
        context['user'] = user
        return context
    
    def post(self, request, *args, **kwargs):
        user = request.user
        
        # Update User model fields
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.save()
        
        # Update UserProfile fields
        profile = user.profile
        profile.whatsapp_number = request.POST.get('whatsapp_number', '')
        profile.national_id = request.POST.get('national_id', '')
        profile.address = request.POST.get('address', '')
        profile.bio = request.POST.get('bio', '')
        
        # Bank account information
        profile.bank_name = request.POST.get('bank_name', '') or None
        profile.bank_account_number = request.POST.get('bank_account_number', '') or None
        profile.bank_account_name = request.POST.get('bank_account_name', '') or None
        
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


class VerificationPendingView(TemplateView):
    """
    Page shown to users whose accounts are awaiting verification.
    """
    template_name = "core/verification_pending.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context


# ============================================================================
# Action Views: GWC, Withdrawal, MESU
# ============================================================================

@login_required
@require_http_methods(["POST"])
def get_gwc_groups(request):
    """Get available GWC groups for user to join"""
    from gwc.models import GWCGroup, GWCGroupMember
    
    user_profile = request.user.profile
    
    # Check if user is already in a group
    existing_membership = GWCGroupMember.objects.filter(user_profile=user_profile).first()
    if existing_membership:
        return JsonResponse({
            'error': 'You are already a member of a GWC group',
            'group_id': existing_membership.group.id,
            'group_name': existing_membership.group.name
        }, status=400)
    
    # Get groups that are accepting members
    # Groups that haven't reached 120M, or groups that have reached 120M (anyone can join)
    groups = GWCGroup.objects.filter(is_active=True).order_by('-created_at')
    
    groups_data = []
    for group in groups:
        groups_data.append({
            'id': group.id,
            'name': group.name,
            'description': group.description,
            'total_contributed': float(group.total_contributed),
            'target_amount': float(group.target_amount),
            'remaining': float(group.remaining_amount),
            'is_complete': group.is_complete,
            'member_count': group.member_count,
            'progress': float(group.progress_percentage)
        })
    
    return JsonResponse({'groups': groups_data})


@login_required
@require_http_methods(["POST"])
def create_gwc_group(request):
    """Create a new GWC group"""
    from gwc.models import GWCGroup
    
    user_profile = request.user.profile
    
    # Check if user is already in a group
    from gwc.models import GWCGroupMember
    if GWCGroupMember.objects.filter(user_profile=user_profile).exists():
        return JsonResponse({'error': 'You are already a member of a GWC group'}, status=400)
    
    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()
    
    if not name:
        return JsonResponse({'error': 'Group name is required'}, status=400)
    
    try:
        group = GWCGroup.objects.create(
            name=name,
            description=description,
            created_by=user_profile
        )
        return JsonResponse({
            'success': True,
            'group_id': group.id,
            'message': 'Group created successfully'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def join_gwc_group(request):
    """Join GWC group (individual or group)"""
    from gwc.models import GWCGroup, GWCGroupMember, GWCContribution
    from savings_52_weeks.models import SavingsTransaction
    
    user_profile = request.user.profile
    
    # Check if user is already in a group
    existing_membership = GWCGroupMember.objects.filter(user_profile=user_profile).first()
    if existing_membership:
        return JsonResponse({
            'error': 'You are already a member of a GWC group',
            'group_id': existing_membership.group.id
        }, status=400)
    
    join_type = request.POST.get('join_type')  # 'individual' or 'group'
    amount = Decimal(request.POST.get('amount', '0'))
    group_id = request.POST.get('group_id')
    
    if amount <= 0:
        return JsonResponse({'error': 'Amount must be greater than 0'}, status=400)
    
    # Get available savings
    try:
        from savings_52_weeks.models import SavingsTransaction
        total_savings = SavingsTransaction.get_user_total_savings(user_profile)
        invested = sum(inv.amount_invested for inv in user_profile.investments.filter(status='fixed'))
        available = total_savings - invested
    except:
        available = Decimal('0.00')
    
    # Check pending withdrawals and MESU holds
    pending_withdrawals = sum(w.amount for w in user_profile.withdrawal_requests.filter(status='pending'))
    pending_mesu = sum(m.total_amount for m in user_profile.mesu_interests.filter(status='pending'))
    available = available - pending_withdrawals - pending_mesu
    
    if amount > available:
        return JsonResponse({
            'error': f'Insufficient funds. Available: UGX {available:,.0f}'
        }, status=400)
    
    try:
        with db_transaction.atomic():
            if join_type == 'individual':
                # Individual join - must have 120M
                if amount < Decimal('120000000'):
                    return JsonResponse({
                        'error': 'Individual membership requires UGX 120,000,000'
                    }, status=400)
                
                # Create group for individual
                group = GWCGroup.objects.create(
                    name=f"{user_profile.user.get_username()}'s Group",
                    description="Individual GWC membership",
                    created_by=user_profile
                )
            else:
                # Group join
                if not group_id:
                    return JsonResponse({'error': 'Group ID is required'}, status=400)
                
                group = get_object_or_404(GWCGroup, id=group_id, is_active=True)
                
                # If group hasn't reached 120M, check minimum contribution
                if not group.is_complete and amount < Decimal('120000000') / Decimal('10'):  # At least 10% of 120M
                    return JsonResponse({
                        'error': f'Minimum contribution: UGX {Decimal("12000000"):,.0f} (until group reaches 120M)'
                    }, status=400)
            
            # Create contribution transaction
            contribution = GWCContribution.objects.create(
                group=group,
                user_profile=user_profile,
                amount=amount,
                receipt_number=f"GWC-{group.id}-{user_profile.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
            )
            
            # Create or update group member
            member, created = GWCGroupMember.objects.get_or_create(
                group=group,
                user_profile=user_profile,
                defaults={'contribution_amount': amount, 'is_leader': (group.created_by == user_profile)}
            )
            
            if not created:
                # Update existing member's contribution
                member.contribution_amount += amount
                member.save()
            
            # Update group totals
            group.total_contributed += amount
            group.check_and_update_status()
            group.save()
            
            # Create withdrawal from savings (deduct from available)
            SavingsTransaction.objects.create(
                user_profile=user_profile,
                amount=amount,
                transaction_type='withdrawal',
                receipt_number=contribution.receipt_number,
                transaction_date=timezone.localdate()
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Successfully joined GWC group: {group.name}',
                'group_id': group.id,
                'contributed': float(amount)
            })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def request_withdrawal(request):
    """Request withdrawal - money is withheld until admin approves"""
    user_profile = request.user.profile
    
    # Check bank account details
    if not user_profile.bank_name or not user_profile.bank_account_number or not user_profile.bank_account_name:
        return JsonResponse({
            'error': 'Bank account details are required. Please update your profile first.'
        }, status=400)
    
    amount = Decimal(request.POST.get('amount', '0'))
    
    if amount <= 0:
        return JsonResponse({'error': 'Amount must be greater than 0'}, status=400)
    
    # Get available savings
    try:
        from savings_52_weeks.models import SavingsTransaction
        total_savings = SavingsTransaction.get_user_total_savings(user_profile)
        invested = sum(inv.amount_invested for inv in user_profile.investments.filter(status='fixed'))
        available = total_savings - invested
    except:
        available = Decimal('0.00')
    
    # Check pending withdrawals and MESU holds
    pending_withdrawals = sum(w.amount for w in user_profile.withdrawal_requests.filter(status='pending'))
    pending_mesu = sum(m.total_amount for m in user_profile.mesu_interests.filter(status='pending'))
    available = available - pending_withdrawals - pending_mesu
    
    if amount > available:
        return JsonResponse({
            'error': f'Insufficient funds. Available: UGX {available:,.0f}'
        }, status=400)
    
    try:
        withdrawal = WithdrawalRequest.objects.create(
            user_profile=user_profile,
            amount=amount,
            bank_name=user_profile.bank_name,
            bank_account_number=user_profile.bank_account_number,
            bank_account_name=user_profile.bank_account_name,
            status='pending'
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Withdrawal request submitted. Admin will process after bank transfer confirmation.',
            'request_id': withdrawal.id
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def express_mesu_interest(request):
    """Express interest in MESU Academy shares - money is held until admin approves"""
    user_profile = request.user.profile
    
    shares = int(request.POST.get('shares', '0'))
    
    if shares <= 0:
        return JsonResponse({'error': 'Number of shares must be greater than 0'}, status=400)
    
    total_amount = Decimal(shares) * Decimal('1000000')  # 1M per share
    
    # Get available savings
    try:
        from savings_52_weeks.models import SavingsTransaction
        total_savings = SavingsTransaction.get_user_total_savings(user_profile)
        invested = sum(inv.amount_invested for inv in user_profile.investments.filter(status='fixed'))
        available = total_savings - invested
    except:
        available = Decimal('0.00')
    
    # Check pending withdrawals and MESU holds
    pending_withdrawals = sum(w.amount for w in user_profile.withdrawal_requests.filter(status='pending'))
    pending_mesu = sum(m.total_amount for m in user_profile.mesu_interests.filter(status='pending'))
    available = available - pending_withdrawals - pending_mesu
    
    if total_amount > available:
        return JsonResponse({
            'error': f'Insufficient funds. Available: UGX {available:,.0f}, Required: UGX {total_amount:,.0f}'
        }, status=400)
    
    try:
        mesu_interest = MESUInterest.objects.create(
            user_profile=user_profile,
            shares_requested=shares,
            total_amount=total_amount,
            status='pending'
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Interest in {shares} MESU share(s) submitted. Admin will process your request.',
            'request_id': mesu_interest.id,
            'total_amount': float(total_amount)
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
