from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from accounts.decorators import project_required
from accounts.models import UserProfile

from .models import (
    Farm,
    InvestmentPackage,
    UserFarmAccount,
    PackagePurchase,
    Payment,
)


@login_required
@project_required("Commercial Goat Farming")
def cgf_dashboard(request):
    user_profile: UserProfile = request.user.profile

    # User's farm accounts
    user_farm_accounts = (
        UserFarmAccount.objects.filter(user=user_profile, is_active=True)
        .select_related("farm")
        .order_by("farm__name", "created_at")
    )

    # User's package purchases
    package_purchases = (
        PackagePurchase.objects.filter(user=user_profile)
        .select_related("package", "farm")
        .order_by("-purchase_date")
    )

    # Aggregates
    total_invested = package_purchases.aggregate(total=Sum("total_amount"))["total"] or 0
    total_paid = package_purchases.aggregate(total=Sum("amount_paid"))["total"] or 0
    total_balance = total_invested - total_paid

    # Total goats across all accounts
    total_goats = user_farm_accounts.aggregate(total=Sum("current_goats"))["total"] or 0

    # Expected kids: package-based total for fallback; per-account uses admin override if set
    allocated_purchases = package_purchases.filter(status='allocated').select_related('package')
    package_based_total = sum(
        p.goats_allocated * getattr(p.package, 'kids_per_goat', 2)
        for p in allocated_purchases
    )
    effective_kids_per_goat = (package_based_total / total_goats) if total_goats else 0

    # Calculate next maturity date (earliest account created + 14 months)
    next_maturity_date = None
    if user_farm_accounts.exists():
        from django.utils import timezone
        from datetime import timedelta
        
        # Get the earliest account creation date and add 14 months (approximately 425 days)
        earliest_account = user_farm_accounts.order_by('created_at').first()
        if earliest_account:
            maturity_date = earliest_account.created_at + timedelta(days=425)  # 14 months ≈ 425 days
            # Only show if it's in the future
            if maturity_date > timezone.now():
                next_maturity_date = maturity_date

    # Recent payments
    recent_payments = (
        Payment.objects.filter(purchase__user=user_profile)
        .select_related("purchase", "purchase__package", "purchase__farm")
        .order_by("-payment_date")[:10]
    )

    # Group accounts by farm; use admin override for expected_kids if set, else calculated
    farms_with_accounts = {}
    total_expected_kids = 0
    for account in user_farm_accounts:
        farm_name = account.farm.name
        if farm_name not in farms_with_accounts:
            farms_with_accounts[farm_name] = {
                'farm': account.farm,
                'accounts': [],
                'total_goats': 0
            }
        resolved_kids = (
            account.expected_kids
            if account.expected_kids is not None
            else int(account.current_goats * effective_kids_per_goat)
        )
        account.resolved_expected_kids = resolved_kids
        total_expected_kids += resolved_kids
        farms_with_accounts[farm_name]['accounts'].append(account)
        farms_with_accounts[farm_name]['total_goats'] += account.current_goats

    context = {
        "user_farm_accounts": user_farm_accounts,
        "farms_with_accounts": farms_with_accounts,
        "package_purchases": package_purchases,
        "recent_payments": recent_payments,
        "total_invested": total_invested,
        "total_paid": total_paid,
        "total_balance": total_balance,
        "total_goats": total_goats,
        "total_expected_kids": total_expected_kids,
        "next_maturity_date": next_maturity_date,
    }

    return render(request, "goat_farming/cgf-dashboard.html", context)


@login_required
@project_required("Commercial Goat Farming")
def investment_page(request):
    """Display investment packages and current investments"""
    user_profile: UserProfile = request.user.profile
    
    # Get available investment packages
    packages = InvestmentPackage.objects.filter(is_active=True).order_by('goat_count')
    
    # Get user's current investments (package purchases)
    current_investments = []
    package_purchases = (
        PackagePurchase.objects.filter(user=user_profile)
        .select_related("package", "farm")
        .order_by("-purchase_date")
    )
    
    for purchase in package_purchases:
        # Calculate expected returns based on package (original + kids)
        kids_per = getattr(purchase.package, 'kids_per_goat', 2)
        expected_returns = purchase.package.goat_count + (purchase.package.goat_count * kids_per)
        
        # Determine status color
        if purchase.status == 'allocated':
            status_color = 'success'
        elif purchase.status == 'paid':
            status_color = 'info'
        elif purchase.status == 'partial':
            status_color = 'warning'
        else:
            status_color = 'secondary'
        
        current_investments.append({
            'id': purchase.id,
            'package_name': purchase.package.name,
            'investment_date': purchase.purchase_date.strftime('%B %d, %Y'),
            'amount': float(purchase.total_amount),
            'status': purchase.get_status_display(),
            'status_color': status_color,
            'expected_returns': expected_returns,
        })
    
    context = {
        'packages': packages,
        'current_investments': current_investments,
    }
    
    return render(request, "goat_farming/investment.html", context)


@login_required
@project_required("Commercial Goat Farming")
@require_http_methods(["GET"])
def investment_details(request, investment_id):
    """Get investment details for modal display"""
    user_profile: UserProfile = request.user.profile
    
    try:
        purchase = get_object_or_404(
            PackagePurchase.objects.select_related("package", "farm"),
            id=investment_id,
            user=user_profile
        )
        
        # Calculate progress (simplified - you can enhance this)
        progress = 0
        if purchase.status == 'allocated':
            progress = 100
        elif purchase.status == 'paid':
            progress = 75
        elif purchase.status == 'partial':
            progress = 50
        else:
            progress = 25
        
        # Expected returns (original + kids using package.kids_per_goat)
        kids_per = getattr(purchase.package, 'kids_per_goat', 2)
        expected_returns = purchase.package.goat_count + (purchase.package.goat_count * kids_per)
        
        # Expected date (simplified - you can enhance this)
        from datetime import timedelta
        expected_date = (purchase.purchase_date + timedelta(days=365)).strftime('%B %d, %Y')
        next_update = (purchase.purchase_date + timedelta(days=30)).strftime('%B %d, %Y')
        
        # Mock updates (you can replace with real data)
        updates = [
            {
                'icon': 'check-circle',
                'color': 'success',
                'message': 'Investment confirmed and goats allocated',
                'date': purchase.purchase_date.strftime('%B %d, %Y')
            },
            {
                'icon': 'clock',
                'color': 'info',
                'message': 'Goats are being prepared for breeding',
                'date': (purchase.purchase_date + timedelta(days=7)).strftime('%B %d, %Y')
            },
            {
                'icon': 'heart',
                'color': 'warning',
                'message': 'Breeding process initiated',
                'date': (purchase.purchase_date + timedelta(days=30)).strftime('%B %d, %Y')
            }
        ]
        
        data = {
            'package_name': purchase.package.name,
            'investment_date': purchase.purchase_date.strftime('%B %d, %Y'),
            'amount': float(purchase.total_amount),
            'status': purchase.get_status_display(),
            'status_color': 'success' if purchase.status == 'allocated' else 'warning',
            'progress': progress,
            'expected_returns': f"{expected_returns} goats",
            'expected_date': expected_date,
            'next_update': next_update,
            'updates': updates,
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': 'Investment not found'}, status=404)


@login_required
@project_required("Commercial Goat Farming")
def transactions_page(request):
    """Display user's transaction history and payment records"""
    user_profile: UserProfile = request.user.profile
    
    # Get user's payments (transactions)
    payments = (
        Payment.objects.filter(purchase__user=user_profile)
        .select_related("purchase", "purchase__package", "purchase__farm")
        .order_by("-payment_date")
    )
    
    # Apply filters
    filter_type = request.GET.get('type', '')
    filter_status = request.GET.get('status', '')
    filter_start_date = request.GET.get('start_date', '')
    filter_end_date = request.GET.get('end_date', '')
    
    if filter_type:
        if filter_type == 'investment':
            payments = payments.filter(purchase__isnull=False)
        elif filter_type == 'fee':
            # You can add management fee transactions here if needed
            pass
    
    if filter_start_date:
        payments = payments.filter(payment_date__gte=filter_start_date)
    if filter_end_date:
        payments = payments.filter(payment_date__lte=filter_end_date)
    
    # Calculate totals
    total_investments = payments.aggregate(total=Sum('amount'))['total'] or 0
    investment_count = payments.count()
    
    # Get package purchases for pending calculations
    package_purchases = PackagePurchase.objects.filter(user=user_profile)
    total_package_amounts = package_purchases.aggregate(total=Sum('total_amount'))['total'] or 0
    total_pending_amount = total_package_amounts - total_investments
    
    # Format transactions for display
    transactions = []
    for payment in payments:
        # Determine transaction type and badge class
        transaction_type = "Investment Payment"
        type_badge_class = "bg-success"
        
        # Determine status and badge class
        if payment.purchase.status == 'allocated':
            status = "Completed"
            status_badge_class = "bg-success"
        elif payment.purchase.status == 'paid':
            status = "Completed"
            status_badge_class = "bg-success"
        elif payment.purchase.status == 'partial':
            status = "Partial"
            status_badge_class = "bg-warning"
        else:
            status = "Pending"
            status_badge_class = "bg-info"
        
        transactions.append({
            'id': payment.id,
            'date': payment.payment_date.strftime('%B %d, %Y'),
            'receipt_no': payment.receipt_number,
            'type': transaction_type,
            'type_badge_class': type_badge_class,
            'description': f"Payment for {payment.purchase.package.name} - {payment.purchase.farm.name}",
            'amount': float(payment.amount),
            'status': status,
            'status_badge_class': status_badge_class,
        })
    
    context = {
        'transactions': transactions,
        'total_investments': total_investments,
        'investment_count': investment_count,
        'total_package_amounts': total_package_amounts,
        'total_pending_amount': total_pending_amount,
        'filter_type': filter_type,
        'filter_status': filter_status,
        'filter_start_date': filter_start_date,
        'filter_end_date': filter_end_date,
    }
    
    return render(request, "goat_farming/transactions.html", context)


@login_required
@project_required("Commercial Goat Farming")
@require_http_methods(["GET"])
def transaction_details(request, transaction_id):
    """Get transaction details for modal display"""
    user_profile: UserProfile = request.user.profile
    
    try:
        payment = get_object_or_404(
            Payment.objects.select_related("purchase", "purchase__package", "purchase__farm"),
            id=transaction_id,
            purchase__user=user_profile
        )
        
        # Determine transaction type and color
        transaction_type = "Investment Payment"
        type_color = "success"
        
        # Determine status and color
        if payment.purchase.status == 'allocated':
            status = "Completed"
            status_color = "success"
        elif payment.purchase.status == 'paid':
            status = "Completed"
            status_color = "success"
        elif payment.purchase.status == 'partial':
            status = "Partial"
            status_color = "warning"
        else:
            status = "Pending"
            status_color = "info"
        
        data = {
            'id': payment.id,
            'date': payment.payment_date.strftime('%B %d, %Y'),
            'type': transaction_type,
            'type_color': type_color,
            'status': status,
            'status_color': status_color,
            'amount': float(payment.amount),
            'description': f"Payment for {payment.purchase.package.name} package at {payment.purchase.farm.name}",
            'payment_method': payment.payment_method or 'Not specified',
            'reference': payment.receipt_number,
            'processed_by': 'System',  # You can enhance this with actual admin user
            'processed_date': payment.created_at.strftime('%B %d, %Y'),
            'notes': payment.notes or 'No additional notes',
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': 'Transaction not found'}, status=404)
