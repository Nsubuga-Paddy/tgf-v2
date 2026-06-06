from django.contrib.auth import get_user_model
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.db import IntegrityError, transaction
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .forms import CustomUserCreationForm
from .models import UserProfile

User = get_user_model()


class MobileTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    JWT login aligned with web `login_view`:
    - username + password (Django AuthenticationForm semantics)
    - inactive users get the same message as the web when credentials are correct
    - returns `user` payload including `is_verified` (tokens issued even if unverified,
      matching web session behavior)
    """

    def validate(self, attrs):
        username = (attrs.get("username") or "").strip()
        password = attrs.get("password") or ""

        if username:
            try:
                user_obj = User.objects.get(username=username)
            except User.DoesNotExist:
                pass
            else:
                if (
                    not user_obj.is_active
                    and password
                    and user_obj.check_password(password)
                ):
                    raise PermissionDenied(
                        detail=(
                            "Your account has been deactivated. "
                            "Please contact an administrator."
                        )
                    )

        data = super().validate(attrs)
        user = self.user
        try:
            is_verified = user.profile.is_verified
        except UserProfile.DoesNotExist:
            is_verified = False

        data["user"] = {
            "username": user.username,
            "email": user.email or "",
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "is_verified": is_verified,
        }
        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        try:
            token["is_verified"] = user.profile.is_verified
        except UserProfile.DoesNotExist:
            token["is_verified"] = False
        return token


class MobileSignupSerializer(serializers.Serializer):
    username = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    whatsapp_number = serializers.CharField()
    password1 = serializers.CharField(write_only=True, trim_whitespace=False)
    password2 = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        form = CustomUserCreationForm(data=attrs)
        if not form.is_valid():
            raise serializers.ValidationError(form.errors)
        whatsapp_number = form.cleaned_data.get("whatsapp_number")
        if UserProfile.objects.filter(whatsapp_number=whatsapp_number).exists():
            raise serializers.ValidationError(
                {"whatsapp_number": ["This WhatsApp number is already registered."]}
            )
        self.context["signup_form"] = form
        return attrs

    def create(self, validated_data):
        form = self.context["signup_form"]
        whatsapp_number = form.cleaned_data.get("whatsapp_number")
        try:
            with transaction.atomic():
                user = form.save()
                try:
                    profile = user.profile
                except UserProfile.DoesNotExist:
                    profile = UserProfile(user=user)
                profile.whatsapp_number = whatsapp_number
                profile.save()
        except IntegrityError:
            raise serializers.ValidationError(
                {"whatsapp_number": ["This WhatsApp number is already registered."]}
            )
        return user


class MobileLogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    default_error_messages = {
        "bad_token": "Refresh token is invalid or expired.",
    }

    def save(self, **kwargs):
        refresh_token = self.validated_data["refresh"]
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            self.fail("bad_token")


class MobilePasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    default_error_messages = {
        "not_found": (
            "This email is not registered in our database. "
            "If you have not signed up yet, please register first."
        ),
        "no_email": (
            "No email address is on file for this account. "
            "Please contact an administrator."
        ),
    }

    def validate_email(self, value):
        email = (value or "").strip().lower()
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            self.fail("not_found")
        if not (user.email or "").strip():
            self.fail("no_email")
        self.context["reset_user"] = user
        return email

    def save(self, **kwargs):
        return self.context["reset_user"]


class MobilePasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password1 = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password2 = serializers.CharField(write_only=True, trim_whitespace=False)

    default_error_messages = {
        "invalid_link": "The password reset link is invalid or has expired.",
    }

    def validate(self, attrs):
        try:
            uid = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            self.fail("invalid_link")

        if not default_token_generator.check_token(user, attrs["token"]):
            self.fail("invalid_link")

        form = SetPasswordForm(
            user,
            {
                "new_password1": attrs["new_password1"],
                "new_password2": attrs["new_password2"],
            },
        )
        if not form.is_valid():
            raise serializers.ValidationError(form.errors)

        self.context["reset_form"] = form
        return attrs

    def save(self, **kwargs):
        self.context["reset_form"].save()
