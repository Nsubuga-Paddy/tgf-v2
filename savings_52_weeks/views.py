# wsc/views.py
from django.shortcuts import render
from accounts.decorators import project_required
from decimal import Decimal
from django.db.models import Sum, Case, When, F, Value, DecimalField
from django.utils import timezone
from .models import SavingsTransaction, Investment
from .interest_utils import calculate_unfixed_interest_ytd, get_expected_full_year_interest

@project_required('52 Weeks Saving Challenge')
def group_dashboard(request):
    # Renders the group overview dashboard page
    user = request.user
    user_profile = user.profile if hasattr(user, 'profile') else None
    
    # Get group aggregate data
    group_data = {}
    
    try:
        # Get all verified users with access to this project
        from accounts.models import UserProfile
        verified_users = UserProfile.objects.filter(
            is_verified=True,
            projects__name='52 Weeks Saving Challenge'
        ).distinct()
        
        print(f"Debug: Found {verified_users.count()} verified users with project access")
        if verified_users.exists():
            print(f"Debug: Users: {[u.user.username for u in verified_users]}")
        
        if verified_users.exists():
            # Calculate group total savings (all deposits minus all withdrawals and GWC contributions)
            total_savings = SavingsTransaction.objects.filter(
                user_profile__in=verified_users
            ).aggregate(
                total=Sum(
                    Case(
                        When(transaction_type='deposit', then=F('amount')),
                        When(transaction_type='withdrawal', then=-F('amount')),
                        When(transaction_type='gwc_contribution', then=-F('amount')),
                        default=Value(0),
                        output_field=DecimalField(max_digits=14, decimal_places=2),
                    )
                )
            )['total'] or Decimal('0.00')
            
            # Calculate group total invested (only fixed investments)
            total_invested = Investment.objects.filter(
                user_profile__in=verified_users,
                status='fixed'
            ).aggregate(
                total=Sum('amount_invested')
            )['total'] or Decimal('0.00')
            
            # Calculate uninvested amount
            uninvested_amount = total_savings - total_invested
            
            # Calculate total interest gained (only fixed investments)
            # We need to calculate this manually since interest_gained_so_far is a property
            fixed_investments = Investment.objects.filter(
                user_profile__in=verified_users,
                status='fixed'
            )
            total_interest_gained_invested = sum(inv.interest_gained_so_far for inv in fixed_investments)
            
            # Calculate 15% interest on uninvested savings (for full 52-week period)
            uninvested_interest = (uninvested_amount * Decimal('0.15')) if uninvested_amount > 0 else Decimal('0.00')
            
            # Calculate total interest from both invested and uninvested savings
            total_interest_gained = total_interest_gained_invested + uninvested_interest
            
            # Calculate progress percentage (total saved vs target)
            target_amount = Decimal('13780000')  # 52 weeks * 10,000 per week
            progress_percentage = min((total_savings / target_amount) * 100, 100) if target_amount > 0 else 0
            
            # Calculate investment rate percentage
            investment_rate = (total_invested / total_savings * 100) if total_savings > 0 else 0
            
            # Calculate current week of the year and weekly progress
            from datetime import date, timedelta
            today = date.today()
            start_of_year = date(today.year, 1, 1)
            days_elapsed = (today - start_of_year).days
            current_week = min(days_elapsed // 7 + 1, 52)  # Cap at week 52
            
            # Calculate required savings for current week
            required_savings = current_week * 10000  # Week N × UGX 10,000
            remaining_weeks = max(52 - current_week, 0)
            
            # Get group investment pools data
            group_investments = Investment.objects.filter(
                user_profile__in=verified_users
            ).select_related('user_profile__user').order_by('-start_date')
            
            print(f"Debug: Found {group_investments.count()} investments")
            
            # Group investments by month for pool overview
            investment_pools = []
            from collections import defaultdict
            monthly_pools = defaultdict(lambda: {
                'total_amount': Decimal('0.00'),
                'members': set(),
                'total_interest_earned': Decimal('0.00'),
                'start_date': None,
                'maturity_date': None,
                'status': 'active'
            })
            
            for investment in group_investments:
                month_key = (investment.start_date.year, investment.start_date.month)
                pool = monthly_pools[month_key]
                pool['total_amount'] += investment.amount_invested
                pool['members'].add(investment.user_profile.user.get_full_name() or investment.user_profile.user.username)
                pool['total_interest_earned'] += investment.interest_gained_so_far
                if not pool['start_date'] or investment.start_date < pool['start_date']:
                    pool['start_date'] = investment.start_date
                if not pool['maturity_date'] or investment.maturity_date > pool['maturity_date']:
                    pool['maturity_date'] = investment.maturity_date
                if investment.status == 'matured':
                    pool['status'] = 'matured'
            
            # Convert to list and format for template
            for (year, month), pool in monthly_pools.items():
                investment_pools.append({
                    'start_date': pool['start_date'],
                    'total_amount': pool['total_amount'],
                    'member_count': len(pool['members']),
                    'total_interest_earned': pool['total_interest_earned'],
                    'maturity_date': pool['maturity_date'],
                    'status': pool['status']
                })
            
            # Sort by start date (newest first)
            investment_pools.sort(key=lambda x: x['start_date'], reverse=True)
            
            print(f"Debug: Created {len(investment_pools)} investment pools")
            for pool in investment_pools:
                print(f"Debug: Pool - {pool['start_date']}: {pool['member_count']} members, UGX {pool['total_amount']}")
            
            # Calculate weekly group savings data - use the model's fully_covered_weeks logic
            weekly_savings = []
            
            # Get all deposit transactions from verified users with their fully_covered_weeks
            user_covered_weeks = {}
            for user_profile in verified_users:
                # Get the latest deposit transaction for this user to see their current coverage
                latest_deposit = SavingsTransaction.objects.filter(
                    user_profile=user_profile,
                    transaction_type='deposit'
                ).order_by('-created_at').first()
                
                if latest_deposit and latest_deposit.fully_covered_weeks:
                    # This user has covered weeks - track which ones
                    user_covered_weeks[user_profile.id] = set()
                    for week_data in latest_deposit.fully_covered_weeks:
                        if week_data.get('fully_covered', False):
                            user_covered_weeks[user_profile.id].add(week_data['week'])
                else:
                    # User has no covered weeks yet
                    user_covered_weeks[user_profile.id] = set()
            
            print(f"Debug: User covered weeks: {user_covered_weeks}")
            
            # For each week, count how many users can fully cover it
            for week in range(1, 53):
                week_target = week * 10000  # Week N × UGX 10,000
                
                # Count users who can cover this week
                users_covering_week = 0
                total_amount_for_week = Decimal('0.00')
                
                for user_id, covered_weeks in user_covered_weeks.items():
                    if week in covered_weeks:
                        users_covering_week += 1
                        total_amount_for_week += week_target  # Only count what's needed for this week
                
                # Determine status
                if users_covering_week > 0:
                    status = 'Complete'
                    investment_status = 'Invested'
                else:
                    status = 'Incomplete'
                    investment_status = 'Pending'
                
                weekly_savings.append({
                    'week': week,
                    'total_amount': total_amount_for_week,
                    'members_contributed': users_covering_week,
                    'status': status,
                    'investment_status': investment_status,
                    'target_amount': week_target,
                    'progress_percentage': min((total_amount_for_week / week_target * 100), 100) if week_target > 0 else 0
                })
            
            # Calculate completed weeks count
            completed_weeks_count = sum(1 for week in weekly_savings if week['status'] == 'Complete')
            
            # Removed duplicate code
            
            # Debug: Print what we're sending to template
            print(f"Debug: weekly_savings length: {len(weekly_savings)}")
            print(f"Debug: investment_pools length: {len(investment_pools)}")
            print(f"Debug: verified_users count: {verified_users.count()}")
            
            # Pagination for weekly savings table
            from django.core.paginator import Paginator
            page_number = request.GET.get('page', 1)
            paginator = Paginator(weekly_savings, 10)  # 10 rows per page
            
            try:
                weekly_savings_page = paginator.page(page_number)
            except:
                weekly_savings_page = paginator.page(1)
            
            group_data = {
                'total_savings': total_savings,
                'total_invested': total_invested,
                'uninvested_amount': uninvested_amount,
                'total_interest_gained': total_interest_gained,
                'total_interest_gained_invested': total_interest_gained_invested,
                'uninvested_interest': uninvested_interest,
                'progress_percentage': progress_percentage,
                'target_amount': target_amount,
                'member_count': verified_users.count(),
                'investment_rate': investment_rate,
                'current_week': current_week,
                'required_savings': required_savings,
                'remaining_weeks': remaining_weeks,
                'investment_pools': investment_pools,
                'weekly_savings': weekly_savings,
                'weekly_savings_page': weekly_savings_page,
                'completed_weeks_count': completed_weeks_count,
            }
    except Exception as e:
        # If there's an error, provide default values
        group_data = {
            'total_savings': Decimal('0.00'),
            'total_invested': Decimal('0.00'),
            'uninvested_amount': Decimal('0.00'),
            'total_interest_gained': Decimal('0.00'),
            'total_interest_gained_invested': Decimal('0.00'),
            'uninvested_interest': Decimal('0.00'),
            'progress_percentage': 0,
            'target_amount': Decimal('13780000'),
            'member_count': 0,
            'investment_rate': 0,
            'current_week': 1,
            'required_savings': 10000,
            'remaining_weeks': 51,
            'investment_pools': [],
            'weekly_savings': [],
            'weekly_savings_page': None,
            'completed_weeks_count': 0,
        }
        print(f"Error in group_dashboard: {e}")  # For debugging
    
    context = {
        'user': user,
        'user_profile': user_profile,
        'group_data': group_data,
    }
    return render(request, "savings_52_weeks/52wsc-dashboard.html", context)

@project_required('52 Weeks Saving Challenge')
def member_savings(request):
    # Renders the member's personal savings page
    user = request.user
    user_profile = user.profile if hasattr(user, 'profile') else None

    # Check for matured fixed deposits and create deposit transactions before loading data
    if user_profile:
        Investment.check_all_investments_status(user_profile=user_profile)

    # Get user's savings data
    savings_data = {}
    if user_profile:
            # Get all transactions (including any newly created matured FD deposits)
            all_transactions = user_profile.savings_transactions.all().order_by('transaction_date', 'created_at')
            
            # Calculate gross deposits (including matured interest deposits)
            # and separately track withdrawals and GWC contributions for reporting.
            total_deposits = Decimal('0.00')
            total_withdrawals = Decimal('0.00')
            total_gwc = Decimal('0.00')
            
            for transaction in all_transactions:
                if transaction.transaction_type == 'deposit':
                    # Includes normal deposits and matured-interest deposits
                    total_deposits += transaction.amount
                elif transaction.transaction_type == 'withdrawal':
                    total_withdrawals += transaction.amount
                elif transaction.transaction_type == 'gwc_contribution':
                    total_gwc += transaction.amount
            
            # Net deposit = deposits - withdrawals - GWC contributions
            # (kept for summaries, but running_total below now tracks deposit pool only)
            net_deposits = total_deposits - total_withdrawals - total_gwc
            
            # Get total savings (includes interest from investments and uninvested savings)
            # This uses the UserProfile method which includes all interest calculations
            total_savings = user_profile.get_total_savings()
            
            # Get challenge progress for current year
            current_year = timezone.now().year
            challenge_progress = SavingsTransaction.get_user_challenge_progress(user_profile, year=current_year)
            
            # Get the most recent transaction (any type) for balance brought forward
            latest_transaction_all_types = user_profile.savings_transactions.all().order_by('-created_at').first()
            
            # Get latest deposit transaction for next week calculation (current year only)
            current_year = timezone.now().year
            latest_deposit_transaction = user_profile.savings_transactions.filter(
                transaction_type='deposit',
                transaction_date__year=current_year
            ).order_by('-created_at').first()
            
            # Calculate balance brought forward based on most recent transaction
            # If last transaction is withdrawal or GWC, balance forward is 0
            # Otherwise, use the remaining_balance from the latest deposit
            if latest_transaction_all_types:
                if latest_transaction_all_types.transaction_type in ('withdrawal', 'gwc_contribution'):
                    balance_brought_forward = Decimal('0.00')
                else:
                    # It's a deposit, use its remaining_balance
                    balance_brought_forward = latest_transaction_all_types.remaining_balance if hasattr(latest_transaction_all_types, 'remaining_balance') else Decimal('0.00')
            else:
                balance_brought_forward = Decimal('0.00')
            
            # Calculate running balance for display (net of deposits, withdrawals, GWC).
            # Deposits (including matured FD principal+interest) increase the balance.
            # Withdrawals and GWC contributions reduce the balance.
            running_total = Decimal('0.00')
            for transaction in all_transactions:
                if transaction.transaction_type == 'deposit':
                    running_total += transaction.amount
                elif transaction.transaction_type in ('withdrawal', 'gwc_contribution'):
                    running_total -= transaction.amount
                transaction.display_running_total = running_total
            
            # Get last 10 transactions for display (newest first)
            transactions = list(all_transactions)[-10:][::-1]  # Last 10, reversed for newest first
            
            # Get investment data
            investments = user_profile.investments.all()
            total_invested = sum(inv.amount_invested for inv in investments if inv.status == 'fixed')
            total_interest_expected = sum(inv.total_interest_expected for inv in investments if inv.status == 'fixed')
            total_interest_gained = sum(inv.interest_gained_so_far for inv in investments if inv.status == 'fixed')
            
            # Calculate uninvested amount based on net deposits (not gross deposits)
            uninvested_amount = net_deposits - total_invested if net_deposits > total_invested else Decimal('0.00')
            
            # Get latest investment's maturity date
            latest_investment = investments.filter(status='fixed').order_by('-start_date').first()
            latest_maturity_date = latest_investment.maturity_date if latest_investment else None
            
            # 15% annualized interest on unfixed savings:
            # - Earned YTD: daily-accrued interest from Jan 1 to today (for Interest Earned card)
            # - Expected full year: estimate if balance stays constant (for reference)
            unfixed_interest_earned_ytd = calculate_unfixed_interest_ytd(user_profile)
            uninvested_interest = get_expected_full_year_interest(user_profile)
            
            # Calculate current week of the year and weekly progress
            from datetime import date
            today = date.today()
            start_of_year = date(today.year, 1, 1)
            days_elapsed = (today - start_of_year).days
            current_week = min(days_elapsed // 7 + 1, 52)  # Cap at week 52
            
            # Calculate required savings for current week
            required_savings = current_week * 10000  # Week N × UGX 10,000
            remaining_weeks = max(52 - current_week, 0)
            
            # Calculate current year deposits only (for Total Savings card display)
            # Only deposits count - withdrawals and GWC contributions affect last year's matured savings
            current_year_deposits = Decimal('0.00')
            for t in all_transactions.filter(transaction_date__year=current_year, transaction_type='deposit'):
                current_year_deposits += t.amount
            
            # Calculate progress percentage based on current year deposits only
            total_target = Decimal('13780000')  # 13,780,000 UGX
            current_year_progress_percentage = (current_year_deposits / total_target * 100) if total_target > 0 else 0
            current_year_progress_percentage = min(current_year_progress_percentage, 100)
            
            savings_data = {
                'total_savings': total_savings,  # Full total including all interest (for other calculations)
                'current_year_deposits': current_year_deposits,  # Current year deposits only (for Total Savings card)
                'net_deposits': net_deposits,  # Running deposit balance (after withdrawals/GWC)
                'total_deposits': total_deposits,  # Gross deposits
                'total_withdrawals': total_withdrawals,  # Total withdrawals
                'total_gwc': total_gwc,  # Total GWC contributions
                'challenge_progress': challenge_progress,
                'latest_transaction': latest_deposit_transaction,
                # Balance brought forward: 0 if last transaction is withdrawal/GWC, 
                # otherwise the remaining_balance from the latest deposit
                'balance_brought_forward': balance_brought_forward,
                'next_week_to_cover': latest_deposit_transaction.next_week if latest_deposit_transaction else 1,
                'weeks_completed': challenge_progress['weeks_completed'],
                'total_weeks': challenge_progress['total_weeks'],
                'progress_percentage': current_year_progress_percentage,  # Based on current year net savings
                'current_week': current_week,
                'required_savings': required_savings,
                'remaining_weeks': remaining_weeks,
                'transactions': transactions,
                'investments': {
                    'total_invested': total_invested,
                    'total_interest_expected': total_interest_expected,
                    'total_interest_gained': total_interest_gained,
                    'uninvested_amount': uninvested_amount,
                    'uninvested_interest': uninvested_interest,
                    'unfixed_interest_earned_ytd': unfixed_interest_earned_ytd,
                    'latest_maturity_date': latest_maturity_date,
                    'investment_list': investments
                }
            }
    
    context = {
        'user': user,
        'user_profile': user_profile,
        'savings_data': savings_data,
    }
    return render(request, "savings_52_weeks/52wsc-member-dashboard.html", context)

