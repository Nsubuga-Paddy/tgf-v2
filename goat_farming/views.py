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

    # Expected kids (2 per goat)
    total_expected_kids = total_goats * 2
    
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

    # Group accounts by farm for better display
    farms_with_accounts = {}
    for account in user_farm_accounts:
        farm_name = account.farm.name
        if farm_name not in farms_with_accounts:
            farms_with_accounts[farm_name] = {
                'farm': account.farm,
                'accounts': [],
                'total_goats': 0
            }
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
        # Calculate expected returns based on package
        expected_returns = purchase.package.goat_count + (purchase.package.goat_count * 2)  # Original + kids
        
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
        
        # Expected returns
        expected_returns = purchase.package.goat_count + (purchase.package.goat_count * 2)
        
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


@login_required
@project_required("Commercial Goat Farming")
def tracking_page(request):
    """Display visual farm tracking with satellite imagery and real-time data"""
    user_profile: UserProfile = request.user.profile
    
    # Get user's farm accounts for tracking data
    user_farm_accounts = (
        UserFarmAccount.objects.filter(user=user_profile, is_active=True)
        .select_related("farm")
        .order_by("farm__name", "created_at")
    )
    
    # Calculate farm statistics
    total_goats = user_farm_accounts.aggregate(total=Sum("current_goats"))["total"] or 0
    healthy_goats = total_goats  # Simplified - you can enhance this with health status
    pregnant_goats = max(0, total_goats // 3)  # Simplified calculation
    total_offspring = total_goats * 2  # Expected offspring
    
    # Create farm zones data for map overlays
    farm_zones = []
    for account in user_farm_accounts:
        farm_zones.append({
            'name': f"{account.farm.name} - Zone {account.id}",
            'goats_count': account.current_goats,
            'area': f"{account.current_goats * 0.1:.1f} ha"  # Simplified area calculation
        })
    
    # Mock satellite data (you can replace with real API calls)
    from django.utils import timezone
    satellite_data = {
        'coverage_area': '5 km²',
        'resolution': '10m',
        'weather_conditions': 'Clear',
        'temperature': '25°C',
        'humidity': '65%',
        'wind_speed': '12 km/h',
        'last_updated': timezone.now()
    }
    
    # Mock farm videos (you can replace with real video data)
    farm_videos = [
        {
            'title': 'Weekly Farm Update',
            'description': 'Latest developments and goat health updates from our farm',
            'youtube_id': 'dQw4w9WgXcQ',
            'date': timezone.now(),
            'category': 'update'
        },
        {
            'title': 'Goat Feeding',
            'description': 'Daily feeding routine and goat behavior',
            'youtube_id': 'dQw4w9WgXcQ',
            'date': timezone.now(),
            'category': 'feeding'
        },
        {
            'title': 'Health Check',
            'description': 'Veterinary examination and health monitoring',
            'youtube_id': 'dQw4w9WgXcQ',
            'date': timezone.now(),
            'category': 'health'
        },
        {
            'title': 'New Kids Born',
            'description': 'Celebrating new additions to our herd',
            'youtube_id': 'dQw4w9WgXcQ',
            'date': timezone.now(),
            'category': 'breeding'
        },
        {
            'title': 'Farm Tour',
            'description': 'Complete tour of our facilities and operations',
            'youtube_id': 'dQw4w9WgXcQ',
            'date': timezone.now(),
            'category': 'tour'
        }
    ]

    # Mock farm photos (you can replace with real photo data)
    farm_photos = [
        {
            'title': 'Healthy Goat Herd',
            'description': 'Our main herd grazing in the morning',
            'image_url': 'https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=500&h=300&fit=crop',
            'category': 'goats',
            'likes': 24,
            'date': timezone.now()
        },
        {
            'title': 'Modern Barn',
            'description': 'Our newly constructed goat shelter',
            'image_url': 'https://images.unsplash.com/photo-1583337130417-3346a1be7dee?w=500&h=300&fit=crop',
            'category': 'facilities',
            'likes': 18,
            'date': timezone.now()
        },
        {
            'title': 'Feeding Time',
            'description': 'Goats enjoying their afternoon meal',
            'image_url': 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=500&h=300&fit=crop',
            'category': 'activities',
            'likes': 32,
            'date': timezone.now()
        },
        {
            'title': 'New Kids',
            'description': 'Recently born kids playing together',
            'image_url': 'https://images.unsplash.com/photo-1544966503-7cc5ac882d5f?w=500&h=300&fit=crop',
            'category': 'goats',
            'likes': 45,
            'date': timezone.now()
        },
        {
            'title': 'Water System',
            'description': 'Automated water dispensing system',
            'image_url': 'https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=500&h=300&fit=crop',
            'category': 'facilities',
            'likes': 12,
            'date': timezone.now()
        },
        {
            'title': 'Health Check',
            'description': 'Veterinary examination in progress',
            'image_url': 'https://images.unsplash.com/photo-1500595046743-cd271d694d30?w=500&h=300&fit=crop',
            'category': 'activities',
            'likes': 28,
            'date': timezone.now()
        }
    ]

    # Mock live cameras (you can replace with real camera feeds)
    live_cameras = [
        {
            'name': 'Main Farm View',
            'description': 'Overview of the main goat grazing area',
            'location': 'main_farm',
            'status': 'live',
            'quality': 'HD'
        },
        {
            'name': 'Feeding Station',
            'description': 'Monitor feeding activities and goat behavior',
            'location': 'feeding_area',
            'status': 'live',
            'quality': 'HD'
        },
        {
            'name': 'Barn Monitoring',
            'description': 'Interior view of the goat shelter',
            'location': 'barn_interior',
            'status': 'live',
            'quality': 'HD'
        }
    ]

    # Mock farm activities (you can replace with real activity tracking)
    farm_activities = [
        {
            'title': 'Health Check Completed',
            'description': 'Routine health check for all zones completed successfully',
            'icon': 'stethoscope',
            'color': 'info',
            'color_rgb': '14,165,233',
            'date': timezone.now()
        },
        {
            'title': 'Feed Distribution',
            'description': 'Morning feed distributed to all zones',
            'icon': 'wheat-awn',
            'color': 'success',
            'color_rgb': '22,163,74',
            'date': timezone.now()
        },
        {
            'title': 'Water Level Check',
            'description': 'All water troughs at optimal levels',
            'icon': 'tint',
            'color': 'primary',
            'color_rgb': '13,110,253',
            'date': timezone.now()
        },
        {
            'title': 'Satellite Scan',
            'description': 'High-resolution satellite imagery captured',
            'icon': 'satellite',
            'color': 'secondary',
            'color_rgb': '108,117,125',
            'date': timezone.now()
        },
        {
            'title': 'Vegetation Analysis',
            'description': 'Pasture health assessment completed',
            'icon': 'leaf',
            'color': 'success',
            'color_rgb': '22,163,74',
            'date': timezone.now()
        }
    ]
    
    context = {
        'satellite_data': satellite_data,
        'farm_zones': farm_zones,
        'total_goats': total_goats,
        'healthy_goats': healthy_goats,
        'pregnant_goats': pregnant_goats,
        'total_offspring': total_offspring,
        'farm_activities': farm_activities,
        'farm_videos': farm_videos,
        'farm_photos': farm_photos,
        'live_cameras': live_cameras,
    }
    
    return render(request, "goat_farming/tracking.html", context)
