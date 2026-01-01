"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings

from .views import (
    LandingPage, LoginPage, SignUpPage, ProfileView, VerificationPendingView,
    get_gwc_groups, create_gwc_group, join_gwc_group,
    request_withdrawal, express_mesu_interest
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", LandingPage.as_view(), name="landing"),
    path("login/", LoginPage.as_view(), name="login"),
    path("signup/", SignUpPage.as_view(), name="signup"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("verification-pending/", VerificationPendingView.as_view(), name="verification_pending"),
    
    # Action endpoints
    path("api/gwc/groups/", get_gwc_groups, name="get_gwc_groups"),
    path("api/gwc/create-group/", create_gwc_group, name="create_gwc_group"),
    path("api/gwc/join/", join_gwc_group, name="join_gwc_group"),
    path("api/withdraw/", request_withdrawal, name="request_withdrawal"),
    path("api/mesu/interest/", express_mesu_interest, name="express_mesu_interest"),
    
    path("accounts/", include("accounts.urls")),
    
    path("52wsc/", include("savings_52_weeks.urls")),
    path("fsa/", include("fixed_savings.urls")),
    path("gwc/", include("gwc.urls")),
    path("cgf/", include("goat_farming.urls")),
    path("clubs-account/", include("clubs_account.urls")),
    path("rss/", include("retirement_savings.urls")),
    path("rep/", include("realestate_projects.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
