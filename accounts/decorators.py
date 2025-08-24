# accounts/decorators.py
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse

def _is_ajax(request) -> bool:
    # Works for fetch/XHR; add more checks if you need
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'

def project_required(project_name):
    """
    Ensure the logged-in user has access to a given project.
    For AJAX (fetch) requests, returns JSON with status and user info.
    For normal requests, uses messages + redirect.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user

            # Not authenticated
            if not user.is_authenticated:
                if _is_ajax(request):
                    return JsonResponse(
                        {
                            "allowed": False,
                            "reason": "auth",
                            "project": project_name,
                            "login_url": reverse("accounts:login") if "accounts:login" else reverse("login"),
                        },
                        status=401,
                    )
                messages.error(request, "Please log in to continue.")
                # Keep 'next' so you can bounce back
                login_url = reverse("accounts:login") if "accounts:login" else reverse("login")
                return redirect(f"{login_url}?next={request.get_full_path()}")

            # Check profile + membership
            has_profile = hasattr(user, "profile")
            has_access = (
                has_profile and user.profile.projects.filter(name=project_name).exists()
            )

            if has_access:
                return view_func(request, *args, **kwargs)

            # No access
            if _is_ajax(request):
                # Return structured info for your front-end
                enrolled = []
                if has_profile:
                    enrolled = list(user.profile.projects.values_list("name", flat=True))

                return JsonResponse(
                    {
                        "allowed": False,
                        "reason": "forbidden",
                        "project": project_name,
                        "user": {
                            "username": user.get_username(),
                            "is_verified": getattr(user.profile, "is_verified", False) if has_profile else False,
                            "has_profile": has_profile,
                            "enrolled_projects": enrolled,
                        },
                        # Optional helper URLs your UI can use
                        "support_url": reverse("support") if "support" else None,
                        "home_url": reverse("home") if "home" else "/",
                    },
                    status=403,
                )

            # Normal request: message + redirect
            messages.warning(
                request,
                f"You do not have access to '{project_name}'. Please contact your administrator for access."
            )
            return redirect("landing" if "landing" else "home")
        return _wrapped_view
    return decorator


def verified_required(view_func):
    """
    Ensure the logged-in user has a verified account.
    Returns JSON for AJAX requests; messages + redirect for normal.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user

        # Not authenticated
        if not user.is_authenticated:
            if _is_ajax(request):
                return JsonResponse(
                    {
                        "allowed": False,
                        "reason": "auth",
                        "login_url": reverse("accounts:login") if "accounts:login" else reverse("login"),
                    },
                    status=401,
                )
            messages.error(request, "Please log in to continue.")
            login_url = reverse("accounts:login") if "accounts:login" else reverse("login")
            return redirect(f"{login_url}?next={request.get_full_path()}")

        # Verified?
        is_verified = hasattr(user, "profile") and getattr(user.profile, "is_verified", False)
        if is_verified:
            return view_func(request, *args, **kwargs)

        # Not verified
        if _is_ajax(request):
            return JsonResponse(
                {
                    "allowed": False,
                    "reason": "not_verified",
                    "user": {
                        "username": user.get_username(),
                        "is_verified": is_verified,
                    },
                    "help_url": reverse("verification_pending") if "verification_pending" else None,
                },
                status=403,
            )

        messages.error(
            request,
            "Your account is awaiting admin verification. Please wait for an administrator to verify your account before accessing the dashboard."
        )
        return redirect("verification_pending")
    return _wrapped_view


# Project-specific shorthands (unchanged)
def fsa_required(view_func):      return project_required("Fixed Savings Account")(view_func)
def gwc_required(view_func):      return project_required("Generational Wealth Creation")(view_func)
def cgf_required(view_func):      return project_required("Commercial Goat Farming")(view_func)
def clubs_account_required(view_func):  return project_required("Clubs Account")(view_func)
def rss_required(view_func):      return project_required("Retirement Savings Scheme")(view_func)
def rep_required(view_func):      return project_required("Real Estate Projects")(view_func)
def coffee_farming_required(view_func): return project_required("Coffee Farming")(view_func)
def cocoa_farming_required(view_func):  return project_required("Cocoa Farming")(view_func)
def wsc_required(view_func):      return project_required("52 Weeks Saving Challenge")(view_func)
