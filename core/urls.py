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

from .views import LandingPage, LoginPage, SignUpPage, ProfileView, VerificationPendingView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", LandingPage.as_view(), name="landing"),
    path("login/", LoginPage.as_view(), name="login"),
    path("signup/", SignUpPage.as_view(), name="signup"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("verification-pending/", VerificationPendingView.as_view(), name="verification_pending"),
    
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
