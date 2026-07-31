"""
URL configuration for core project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

from main_account.views import history_csv as main_account_history_csv

from .spa import ReactAppView

# Legacy Django HTML portals (kept for admin/group tooling & old bookmarks).
# The member-facing React SPA is the catch-all below.
urlpatterns = [
    path("api/", include("core.api_urls")),
    path("api/", include("accounts.api_urls")),
    path("admin/", admin.site.urls),
    path("main-account/history.csv", main_account_history_csv, name="main_account_history_csv"),
    path("accounts/", include("accounts.urls")),
    path("52wsc/", include("savings_52_weeks.urls")),
    path("fsa/", include("fixed_savings.urls")),
    path("gwc/", include("gwc.urls")),
    path("cgf/", include("goat_farming.urls")),
    path("clubs-account/", include("clubs_account.urls")),
    path("rss/", include("retirement_savings.urls")),
    path("rep/", include("realestate_projects.urls")),
    # React SPA (same origin as /api). Must stay last.
    path("", ReactAppView.as_view(), name="landing"),
    path("login/", ReactAppView.as_view(), name="login"),
    path("signup/", ReactAppView.as_view(), name="signup"),
    path("profile/", ReactAppView.as_view(), name="profile"),
    path("verification-pending/", ReactAppView.as_view(), name="verification_pending"),
    re_path(r"^(?:help|protection|forgot-password|forgot_password|reset-password|reset_password|projects|reset)/", ReactAppView.as_view()),
    re_path(r"^(?!api/|admin/|static/|media/|accounts/|52wsc/|fsa/|gwc/|cgf/|clubs-account/|rss/|rep/).*$", ReactAppView.as_view()),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
