# accounts/views.py
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import PasswordResetConfirmView, PasswordResetCompleteView
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.http import url_has_allowed_host_and_scheme
from django.conf import settings

from .forms import CustomUserCreationForm, PasswordResetRequestForm
from .models import UserProfile

User = get_user_model()

# --- Helpers ---
def _find_user_by_username_email_phone(value):
    """
    Find a User by username, email, or profile whatsapp_number.
    Returns (user, None) if found, (None, error_message) if not found or no email.
    """
    value = (value or "").strip()
    if not value:
        return None, "Please enter your username, email or phone number."

    # Try username (exact)
    user = User.objects.filter(username=value).first()
    if user:
        if not user.email:
            return None, "No email address is on file for this account. Please contact an administrator to reset your password."
        return user, None

    # Try email (case-insensitive)
    user = User.objects.filter(email__iexact=value).first()
    if user:
        if not user.email:
            return None, "No email address is on file for this account. Please contact an administrator to reset your password."
        return user, None

    # Try phone (normalize with phonenumber_field if possible)
    try:
        from phonenumber_field.phonenumber import PhoneNumber
        pn = PhoneNumber.from_string(value, region="UG")
        if pn and pn.is_valid():
            profile = UserProfile.objects.filter(whatsapp_number=pn).first()
            if profile:
                user = profile.user
                if not getattr(user, "email", None) or not user.email.strip():
                    return None, "No email address is on file for this account. Please contact an administrator to reset your password."
                return user, None
    except Exception:
        pass
    # Also try raw string match for whatsapp_number (stored format may match)
    profile = UserProfile.objects.filter(whatsapp_number=value).first()
    if profile:
        user = profile.user
        if not getattr(user, "email", None) or not user.email.strip():
            return None, "No email address is on file for this account. Please contact an administrator to reset your password."
        return user, None

    return None, "No account found with that username, email or phone number. Please check and try again."


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
            messages.warning(
                request,
                (
                    f"Welcome back, {user.get_username()}! Your account is pending "
                    "verification. You will be redirected to the verification pending page."
                ),
            )
            return redirect("verification_pending")

    # When login fails, determine and pass a clear reason for the user
    login_error = None
    if request.method == "POST" and not form.is_valid():
        username = (request.POST.get("username") or "").strip()
        if username:
            try:
                user_obj = User.objects.get(username=username)
                if not user_obj.is_active:
                    login_error = (
                        "Your account has been deactivated. "
                        "Please contact an administrator."
                    )
            except User.DoesNotExist:
                # User with this username does not exist; fall back to generic errors
                pass

        # If we still don't have a custom message, use the form's non-field error
        non_field_errors = form.non_field_errors()
        if login_error is None and non_field_errors:
            login_error = non_field_errors[0]

        # Final fallback message
        if login_error is None:
            login_error = (
                "Invalid username or password. "
                "Please check your credentials and try again."
            )

    # keep ?next in the form so it posts through
    context = {
        "form": form,
        "next": request.GET.get("next", ""),
        "login_error": login_error,
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


# --- Password reset (forgot password) ---
def password_reset_request(request):
    """
    Forgot password: user enters username, email or phone.
    We find the user and send a password reset link to their email.
    """
    if request.user.is_authenticated:
        messages.info(request, "You are already signed in.")
        return redirect("landing")

    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            value = form.cleaned_data["username_email_phone"]
            user, error = _find_user_by_username_email_phone(value)
            if error:
                messages.error(request, error)
                return render(request, "core/forgot_password.html", {"form": form})

            # Generate reset link
            token = default_token_generator.make_token(user)
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            reset_url = request.build_absolute_uri(
                reverse("accounts:password_reset_confirm", kwargs={"uidb64": uidb64, "token": token})
            )
            subject = "Reset your MCS password"
            message = (
                f"Hello {user.get_username()},\n\n"
                f"You requested a password reset. Click the link below to set a new password:\n\n"
                f"{reset_url}\n\n"
                f"If you did not request this, ignore this email. The link expires in 24 hours.\n\n"
                f"— MCS"
            )
            try:
                send_mail(
                    subject,
                    message,
                    getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@mcs.local"),
                    [user.email],
                    fail_silently=False,
                )
            except Exception as e:
                messages.error(
                    request,
                    "We could not send the reset email. Please try again later or contact support.",
                )
                return render(request, "core/forgot_password.html", {"form": form})

            return redirect("accounts:password_reset_done")
    else:
        form = PasswordResetRequestForm()

    return render(request, "core/forgot_password.html", {"form": form})


def password_reset_done(request):
    """Shown after user submits forgot-password: 'Check your email'."""
    return render(request, "core/password_reset_done.html")


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """Set new password from the link in the email."""
    template_name = "core/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    """Shown after password has been changed."""
    template_name = "core/password_reset_complete.html"

