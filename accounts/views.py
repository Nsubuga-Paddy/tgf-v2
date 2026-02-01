# accounts/views.py
import logging
import smtplib

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import PasswordResetConfirmView, PasswordResetCompleteView
from django.core.mail import send_mail, BadHeaderError
from django.shortcuts import render, redirect
from django.template import TemplateDoesNotExist, TemplateSyntaxError
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy, NoReverseMatch
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.http import url_has_allowed_host_and_scheme
from django.conf import settings

from .forms import CustomUserCreationForm, PasswordResetRequestForm
from .models import UserProfile

User = get_user_model()
logger = logging.getLogger(__name__)

# --- Helpers ---
def _find_user_by_email(email):
    """
    Find a User by email (case-insensitive).
    Returns (user, None) if found, (None, error_message) if not found or no email.
    """
    email = (email or "").strip().lower()
    if not email:
        return None, "Please enter your email address."

    user = User.objects.filter(email__iexact=email).first()
    if not user:
        return None, "This email is not registered in our database. If you have not signed up yet, please register first."
    if not (getattr(user, "email", None) and user.email.strip()):
        return None, "No email address is on file for this account. Please contact an administrator."
    return user, None


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
    Forgot password: user enters email only.
    If email exists we send a reset link and show success; otherwise we say email is not registered.
    """
    if request.user.is_authenticated:
        messages.info(request, "You are already signed in.")
        return redirect("landing")

    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            user, error = _find_user_by_email(email)
            if error:
                messages.error(request, error)
                return render(request, "core/forgot_password.html", {"form": form})

            # Build email and send (wrap all in try so template/URL/send errors are caught)
            try:
                token = default_token_generator.make_token(user)
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                subject = "Reset your MCS password"
                message = render_to_string(
                    "core/password_reset_email.html",
                    {
                        "user": user,
                        "protocol": request.scheme,
                        "domain": request.get_host(),
                        "uid": uidb64,
                        "token": token,
                    },
                    request=request,
                )
                send_mail(
                    subject,
                    message,
                    getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@mcs.local"),
                    [user.email],
                    fail_silently=False,
                )
            except NoReverseMatch as e:
                logger.exception(
                    "Password reset failed (URL reverse in template): %s. Check password_reset_email.html and URL name 'accounts:password_reset_confirm'.",
                    e,
                )
                msg = "We could not prepare the reset email (configuration error). Please contact support."
                if settings.DEBUG:
                    msg += f" [Debug: {type(e).__name__}: {e!s}]"
                messages.error(request, msg)
                return render(request, "core/forgot_password.html", {"form": form})
            except (TemplateDoesNotExist, TemplateSyntaxError) as e:
                logger.exception(
                    "Password reset failed (template): %s. Check core/password_reset_email.html.",
                    e,
                )
                msg = "We could not prepare the reset email (template error). Please contact support."
                if settings.DEBUG:
                    msg += f" [Debug: {type(e).__name__}: {e!s}]"
                messages.error(request, msg)
                return render(request, "core/forgot_password.html", {"form": form})
            except smtplib.SMTPAuthenticationError as e:
                logger.exception(
                    "Password reset email failed (SMTP auth): %s. Check EMAIL_HOST_USER and EMAIL_HOST_PASSWORD.",
                    e,
                )
                msg = (
                    "We could not send the reset email (authentication failed). "
                    "Please try again later or contact support."
                )
                if settings.DEBUG:
                    msg += f" [Debug: {e!s}]"
                messages.error(request, msg)
                return render(request, "core/forgot_password.html", {"form": form})
            except smtplib.SMTPRecipientsRefused as e:
                logger.exception("Password reset email failed (recipient refused): %s", e)
                msg = "We could not send the reset email (recipient refused). Please contact support."
                if settings.DEBUG:
                    msg += f" [Debug: {e!s}]"
                messages.error(request, msg)
                return render(request, "core/forgot_password.html", {"form": form})
            except smtplib.SMTPException as e:
                logger.exception("Password reset email failed (SMTP): %s", e)
                msg = "We could not send the reset email. Please try again later or contact support."
                if settings.DEBUG:
                    msg += f" [Debug: {type(e).__name__}: {e!s}]"
                messages.error(request, msg)
                return render(request, "core/forgot_password.html", {"form": form})
            except (OSError, ConnectionError) as e:
                logger.exception(
                    "Password reset email failed (connection): %s. Check EMAIL_HOST and network.",
                    e,
                )
                msg = "We could not send the reset email (connection error). Please try again later."
                if settings.DEBUG:
                    msg += f" [Debug: {e!s}]"
                messages.error(request, msg)
                return render(request, "core/forgot_password.html", {"form": form})
            except BadHeaderError as e:
                logger.exception("Password reset email failed (bad header): %s", e)
                msg = "We could not send the reset email (invalid content). Please contact support."
                if settings.DEBUG:
                    msg += f" [Debug: {e!s}]"
                messages.error(request, msg)
                return render(request, "core/forgot_password.html", {"form": form})
            except Exception as e:
                logger.exception(
                    "Password reset failed (unexpected): %s. Check logs for traceback (template, URL, or send_mail).",
                    e,
                )
                msg = "We could not send the reset email. Please try again later or contact support."
                if settings.DEBUG:
                    msg += f" [Debug: {type(e).__name__}: {e!s}]"
                messages.error(request, msg)
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

