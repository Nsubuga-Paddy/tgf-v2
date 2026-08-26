from django.urls import path

from .api_views import (
    CgfAPIView,
    CgfTransferToMainAPIView,
    ClaimDividendAPIView,
    DashboardAPIView,
    GwcAPIView,
    GwcRedeemInterestAPIView,
    HelpVideosAPIView,
    MainAccountWithdrawAPIView,
    ProfileAPIView,
    ProjectAccessRequestAPIView,
    RepDetailAPIView,
    RepRefundRequestAPIView,
    RepListAPIView,
    Savings52APIView,
    Savings52StartNewCycleAPIView,
    Savings52TransferAllAPIView,
    Savings52TransferPotAPIView,
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
    path(
        "shareholding/claim-dividend/",
        ClaimDividendAPIView.as_view(),
        name="api_shareholding_claim_dividend",
    ),
    path("projects/52wsc/", Savings52APIView.as_view(), name="api_projects_52wsc"),
    path(
        "projects/52wsc/start-new-cycle/",
        Savings52StartNewCycleAPIView.as_view(),
        name="api_projects_52wsc_start_new_cycle",
    ),
    path(
        "projects/52wsc/transfer-all/",
        Savings52TransferAllAPIView.as_view(),
        name="api_projects_52wsc_transfer_all",
    ),
    path(
        "projects/52wsc/transfer-pot/",
        Savings52TransferPotAPIView.as_view(),
        name="api_projects_52wsc_transfer_pot",
    ),
    path("projects/cgf/", CgfAPIView.as_view(), name="api_projects_cgf"),
    path(
        "projects/cgf/transfer-to-main/",
        CgfTransferToMainAPIView.as_view(),
        name="api_projects_cgf_transfer_to_main",
    ),
    path("projects/gwc/", GwcAPIView.as_view(), name="api_projects_gwc"),
    path(
        "projects/gwc/redeem-interest/",
        GwcRedeemInterestAPIView.as_view(),
        name="api_projects_gwc_redeem_interest",
    ),
    path("projects/rep/", RepListAPIView.as_view(), name="api_projects_rep"),
    path(
        "projects/rep/<int:project_id>/",
        RepDetailAPIView.as_view(),
        name="api_projects_rep_detail",
    ),
    path(
        "projects/rep/<int:project_id>/refund/",
        RepRefundRequestAPIView.as_view(),
        name="api_projects_rep_refund",
    ),
    path("help/videos/", HelpVideosAPIView.as_view(), name="api_help_videos"),
]
