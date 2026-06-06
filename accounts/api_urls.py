from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .api_views import (
    MobileLogoutView,
    MobilePasswordResetConfirmView,
    MobilePasswordResetRequestView,
    MobileSignupView,
    MobileTokenObtainPairView,
)

urlpatterns = [
    path("auth/login/", MobileTokenObtainPairView.as_view(), name="mobile_login"),
    path("auth/logout/", MobileLogoutView.as_view(), name="mobile_logout"),
    path(
        "auth/forgot-password/",
        MobilePasswordResetRequestView.as_view(),
        name="mobile_forgot_password",
    ),
    path(
        "auth/reset-password/",
        MobilePasswordResetConfirmView.as_view(),
        name="mobile_reset_password",
    ),
    path("auth/signup/", MobileSignupView.as_view(), name="mobile_signup"),
    path(
        "auth/token/refresh/",
        TokenRefreshView.as_view(),
        name="mobile_token_refresh",
    ),
]
