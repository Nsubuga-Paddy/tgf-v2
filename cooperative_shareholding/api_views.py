from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api_views import serialize_shareholding_summary

from .models import CooperativeShareholding
from .services import build_share_purchase_options, purchase_shares_from_main_account


class SharePurchaseOptionsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(build_share_purchase_options(request.user.profile))


class SharePurchaseFromMainAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        data = request.data or {}
        notes = (data.get("notes") or "").strip()
        raw_shares = data.get("shares")
        if raw_shares is None or raw_shares == "":
            raw_shares = data.get("quantity")
        try:
            shares = Decimal(str(raw_shares or "0").replace(",", ""))
        except (InvalidOperation, TypeError, ValueError):
            return Response(
                {"detail": "Enter a valid number of shares."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = purchase_shares_from_main_account(
                request.user.profile,
                shares,
                notes=notes,
            )
        except (ValueError, ValidationError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        after = result["after"]
        election_open = False
        try:
            election_open = bool(request.user.cooperative_shareholding.dividend_election_open)
        except CooperativeShareholding.DoesNotExist:
            election_open = False

        return Response(
            {
                "ok": True,
                "message": (
                    f"Purchased {result['shares_purchased_display']} share(s) for "
                    f"UGX {result['amount']:,.0f}. You are now "
                    f"{after.get('tier_emoji', '')} {after.get('tier', 'Shareholder')}."
                ).strip(),
                "purchase": {
                    "reference": result["transaction_reference"],
                    "shares": float(result["shares_purchased"]),
                    "sharesDisplay": result["shares_purchased_display"],
                    "amount": float(result["amount"]),
                    "pricePerShare": float(result["price_per_share"]),
                    "tierBefore": result["before"].get("tier"),
                    "tierAfter": after.get("tier"),
                    "tierAfterEmoji": after.get("tier_emoji"),
                    "sharesAfter": after.get("total_shares_display"),
                    "notes": result["notes"],
                },
                "shareholding": serialize_shareholding_summary(
                    after,
                    is_shareholder=True,
                    election_open=election_open,
                    display_state="full",
                ),
                "purchaseOptions": build_share_purchase_options(request.user.profile),
            }
        )
