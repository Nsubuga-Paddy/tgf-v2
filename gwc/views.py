from django.shortcuts import render

from accounts.decorators import project_required

from .models import GWCFixedDeposit
from .services import (
    deposit_to_display,
    portfolio_summary_for_user,
    recent_activities_for_user,
)


@project_required("Generational Wealth Creation")
def gwc_dashboard(request):
    user = request.user
    user_profile = getattr(user, "profile", None)

    deposits_qs = GWCFixedDeposit.objects.filter(user=user).order_by("-start_date", "-pk")
    deposits = [deposit_to_display(d) for d in deposits_qs]

    portfolio = portfolio_summary_for_user(user)
    recent_activities = recent_activities_for_user(user, limit=25)

    return render(
        request,
        "gwc/gwc-dashboard.html",
        {
            "user_profile": user_profile,
            "portfolio": portfolio,
            "deposits": deposits,
            "recent_activities": recent_activities,
        },
    )
