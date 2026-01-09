# accounts/views.py
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.conf import settings

from .forms import CustomUserCreationForm

# --- Helpers ---
def _safe_next_url(request, default_name="landing"):
    """
    Return a safe redirect target from ?next=, otherwise a sensible default.
    """
    next_url = request.GET.get("next") or request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return next_url
    return reverse(default_name)

# --- Auth views ---
def signup(request):
    """
    Basic signup:
    - Prevents already-authenticated users from accessing
    - Uses CustomUserCreationForm
    - Creates User and basic UserProfile
    """
    if request.user.is_authenticated:
        messages.info(request, "You're already signed in.")
        return redirect("landing")

    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # Get the whatsapp_number from the form before saving
            whatsapp_number = form.cleaned_data.get('whatsapp_number')
            
            # Save the user first (signal will try to create profile but may fail without phone)
            user = form.save()
            
            # Create or update the profile with the phone number
            # The signal may have failed to create the profile due to missing whatsapp_number
            from .models import UserProfile
            try:
                profile = user.profile
            except UserProfile.DoesNotExist:
                # Profile doesn't exist (signal failed), create it now
                profile = UserProfile(user=user)
            
            # Set the phone number and save
            profile.whatsapp_number = whatsapp_number
            profile.save()
            
            messages.success(request, f"Account created for {user.username}! Your account is now pending verification by an administrator. You will be able to access the dashboard once verified.")
            return redirect("accounts:login")
    else:
        form = CustomUserCreationForm()

    return render(request, "core/signup.html", {"form": form})


def login_view(request):
    """
    Basic login:
    - Prevents already-authenticated users from accessing
    - Uses AuthenticationForm for validation
    - Honors ?next=
    """
    if request.user.is_authenticated:
        messages.info(request, "You're already signed in.")
        return redirect("landing")

    form = AuthenticationForm(request, data=request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        
        # Check if user is verified
        if hasattr(user, 'profile') and user.profile.is_verified:
            messages.success(request, f"Welcome back, {user.get_username()}!")
            return redirect(_safe_next_url(request, default_name="landing"))
        else:
            messages.warning(request, f"Welcome back, {user.get_username()}! Your account is pending verification. You will be redirected to the verification pending page.")
            return redirect("verification_pending")

    # keep ?next in the form so it posts through
    context = {
        "form": form,
        "next": request.GET.get("next", ""),
    }
    return render(request, "core/login.html", context)


def logout_view(request):
    """
    Logs the user out and sends them to the login page.
    """
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, "You have been successfully logged out.")
    return redirect("accounts:login")

