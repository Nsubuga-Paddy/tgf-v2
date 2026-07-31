from django.urls import path

from .api_views import (
    CgfAPIView,
    DashboardAPIView,
    GwcAPIView,
    HelpVideosAPIView,
    MainAccountWithdrawAPIView,
    ProfileAPIView,
    ProjectAccessRequestAPIView,
    RepDetailAPIView,
    RepListAPIView,
    Savings52APIView,
    VerificationPendingAPIView,
)

urlpatterns = [
    path("dashboard/", DashboardAPIView.as_view(), name="api_dashboard"),
    path("profile/", ProfileAPIView.as_view(), name="api_profile"),
    path(
        "verification/",
        VerificationPendingAPIView.as_view(),
        name="api_verification_pending",
    ),
    path(
        "project-access/",
        ProjectAccessRequestAPIView.as_view(),
        name="api_project_access",
    ),
    path(
        "main-account/withdraw/",
        MainAccountWithdrawAPIView.as_view(),
        name="api_main_account_withdraw",
    ),
    path("projects/52wsc/", Savings52APIView.as_view(), name="api_projects_52wsc"),
    path("projects/cgf/", CgfAPIView.as_view(), name="api_projects_cgf"),
    path("projects/gwc/", GwcAPIView.as_view(), name="api_projects_gwc"),
    path("projects/rep/", RepListAPIView.as_view(), name="api_projects_rep"),
    path(
        "projects/rep/<int:project_id>/",
        RepDetailAPIView.as_view(),
        name="api_projects_rep_detail",
    ),
    path("help/videos/", HelpVideosAPIView.as_view(), name="api_help_videos"),
]
