import logging

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import BadHeaderError, send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    MobileLogoutSerializer,
    MobilePasswordResetConfirmSerializer,
    MobilePasswordResetRequestSerializer,
    MobileSignupSerializer,
    MobileTokenObtainPairSerializer,
)

logger = logging.getLogger(__name__)


class MobileTokenObtainPairView(TokenObtainPairView):
    serializer_class = MobileTokenObtainPairSerializer


class MobileSignupView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = MobileSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "message": (
                    "Account created successfully. Your account is pending "
                    "verification by an administrator. Verifying and updating "
                    "your account may take up to 24hrs. If not, contact support."
                ),
                "support_whatsapp_url": "https://wa.me/256755142271",
                "support_phone": "+256755142271",
                "user": {
                    "username": user.username,
                    "email": user.email or "",
                    "first_name": user.first_name or "",
                    "last_name": user.last_name or "",
                    "is_verified": False,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class MobileLogoutView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = MobileLogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Logged out successfully."},
            status=status.HTTP_205_RESET_CONTENT,
        )


class MobilePasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = MobilePasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        token = default_token_generator.make_token(user)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
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

        try:
            send_mail(
                "Reset your MCS password",
                message,
                getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@mcsug.org"),
                [user.email],
                fail_silently=False,
            )
        except BadHeaderError:
            logger.exception("Mobile password reset email failed (bad header).")
            return Response(
                {"detail": "We could not send the reset email. Please contact support."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception:
            logger.exception("Mobile password reset email failed.")
            return Response(
                {
                    "detail": (
                        "We could not send the reset email. "
                        "Please try again later or contact support."
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "message": (
                    "If the email address is registered, a password reset link "
                    "has been sent."
                )
            },
            status=status.HTTP_200_OK,
        )


class MobilePasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = MobilePasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Password reset successfully. You can now log in."},
            status=status.HTTP_200_OK,
        )
