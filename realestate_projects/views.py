from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.models import UserProfile
from accounts.decorators import project_required

from .models import (
    RealEstateProject,
    RealEstateProjectInterest,
    RealEstateProjectJoinRequest,
    RealEstateProjectTransaction,
)


@project_required("Real Estate Projects")
def real_estate_projects_dashboard(request):
    user_profile = getattr(request.user, "profile", None)

    # All users with access to this module can see the list of running and
    # closed projects, but only projects where they are in allowed_members
    # expose full details.
    running_qs = RealEstateProject.objects.filter(
        status=RealEstateProject.STATUS_RUNNING,
    ).distinct()
    closed_qs = RealEstateProject.objects.filter(
        status=RealEstateProject.STATUS_CLOSED,
    ).distinct()
    # Upcoming projects are visible to all module users so they can express interest.
    upcoming_qs = RealEstateProject.objects.filter(
        status=RealEstateProject.STATUS_UPCOMING,
    ).distinct()

    running_projects = list(
        running_qs.annotate(members_count=Count("allowed_members", distinct=True))
    )
    closed_projects = list(
        closed_qs.annotate(members_count=Count("allowed_members", distinct=True))
    )
    upcoming_projects = list(upcoming_qs)

    # Mark whether the current user is already a member or has a pending join request
    pending_requests = {
        jr.project_id
        for jr in RealEstateProjectJoinRequest.objects.filter(
            user=request.user,
            status=RealEstateProjectJoinRequest.STATUS_PENDING,
        )
    }

    for project in running_projects:
        # Full-detail access if the user is explicitly allowed on this project.
        project.user_has_access = project.allowed_members.filter(
            pk=request.user.pk
        ).exists()
        project.user_has_joined = project.user_has_access
        project.user_has_pending_request = project.id in pending_requests

    for project in closed_projects:
        project.user_has_access = project.allowed_members.filter(
            pk=request.user.pk
        ).exists()

    sidebar_projects = [
        p
        for p in running_projects
        if p.show_in_sidebar
    ]

    context = {
        "user_profile": user_profile,
        "running_projects": running_projects,
        "closed_projects": closed_projects,
        "upcoming_projects": upcoming_projects,
        "sidebar_projects": sidebar_projects,
    }
    return render(request, "realestate_projects/rep-dashboard.html", context)


@require_POST
@project_required("Real Estate Projects")
def request_join_project(request, pk):
    project = get_object_or_404(
        RealEstateProject,
        pk=pk,
        status=RealEstateProject.STATUS_RUNNING,
    )

    # Create or reuse a pending join request
    RealEstateProjectJoinRequest.objects.get_or_create(
        project=project,
        user=request.user,
        defaults={},
    )

    return redirect(request.META.get("HTTP_REFERER") or reverse("realestate_projects:rep"))


@require_POST
@project_required("Real Estate Projects")
def submit_interest(request, pk):
    project = get_object_or_404(
        RealEstateProject,
        pk=pk,
        status=RealEstateProject.STATUS_UPCOMING,
    )

    RealEstateProjectInterest.objects.get_or_create(
        project=project,
        user=request.user,
        defaults={},
    )

    return redirect(request.META.get("HTTP_REFERER") or reverse("realestate_projects:rep"))


@project_required("Real Estate Projects")
def project_detail(request, pk):
    user_profile = getattr(request.user, "profile", None)
    project = get_object_or_404(RealEstateProject, pk=pk)

    user_has_access = project.allowed_members.filter(pk=request.user.pk).exists()

    transactions = RealEstateProjectTransaction.objects.filter(project=project)

    # Derive completed vs partial from transaction payment_status (full vs partial)
    completed_user_ids = set(
        transactions.filter(
            payment_status=RealEstateProjectTransaction.PAYMENT_STATUS_FULL,
        ).values_list("user_id", flat=True).distinct()
    )
    all_transaction_user_ids = set(
        transactions.values_list("user_id", flat=True).distinct()
    )
    partial_user_ids = all_transaction_user_ids - completed_user_ids

    completed_members_count = len(completed_user_ids)
    incomplete_members_count = len(partial_user_ids)

    completed_payments_total = transactions.filter(
        payment_status=RealEstateProjectTransaction.PAYMENT_STATUS_FULL,
    ).aggregate(total=Sum("amount"))["total"] or 0
    partial_payments_total = transactions.filter(
        payment_status=RealEstateProjectTransaction.PAYMENT_STATUS_PARTIAL,
    ).aggregate(total=Sum("amount"))["total"] or 0

    user_transactions = RealEstateProjectTransaction.objects.filter(
        project=project,
        user=request.user,
    ).order_by("-created_at")

    user_total_paid = 0
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
        latest_user_txn.balance_after if latest_user_txn and latest_user_txn.balance_after is not None else None
    )
    user_payment_completed = user_transactions.filter(
        payment_status=RealEstateProjectTransaction.PAYMENT_STATUS_FULL
    ).exists()

    context = {
        "user_profile": user_profile,
        "project": project,
        "user_has_access": user_has_access,
        "completed_members_count": completed_members_count,
        "completed_payments_total": completed_payments_total,
        "incomplete_members_count": incomplete_members_count,
        "partial_payments_total": partial_payments_total,
        "user_transactions": user_transactions,
        "user_total_paid": user_total_paid,
        "user_pending_balance": user_pending_balance,
        "user_payment_completed": user_payment_completed,
    }
    return render(request, "realestate_projects/rep-project-detail.html", context)
