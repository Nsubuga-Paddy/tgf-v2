"""
Django admin for GWC fixed deposits — streamlined recording workflow.
"""
from __future__ import annotations

from decimal import Decimal

from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html

from .models import GWCDepositActivity, GWCFixedDeposit, GWCInterestRedemption
from .services import monthly_interest_ledger


class GWCDepositActivityInline(admin.TabularInline):
    """Optional lines that appear on the member Activity panel (e.g. interest accrual)."""

    model = GWCDepositActivity
    extra = 0
    fields = ("timestamp", "activity_type", "description", "amount")
    ordering = ("-timestamp",)
    classes = ("collapse",)


class GWCInterestRedemptionInline(admin.TabularInline):
    model = GWCInterestRedemption
    extra = 0
    fields = ("amount", "redeemed_at", "notes", "main_account_transaction", "created_by")
    readonly_fields = fields
    can_delete = False
    classes = ("collapse",)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(GWCFixedDeposit)
class GWCFixedDepositAdmin(admin.ModelAdmin):
    list_display = (
        "deposit_id",
        "member_display",
        "receipt_number",
        "principal_amount",
        "transaction_date",
        "start_date",
        "maturity_date",
        "interest_rate",
        "redeemable_monthly_interest",
        "redeemable_balance_display",
        "status",
    )
    list_filter = ("status", "redeemable_monthly_interest", "start_date", "interest_method")
    list_editable = ("redeemable_monthly_interest",)
    autocomplete_fields = ("user",)
    search_fields = (
        "deposit_id",
        "receipt_number",
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
    )
    readonly_fields = ("deposit_id", "created_at", "updated_at", "redeemable_balance_display")
    inlines = (GWCDepositActivityInline, GWCInterestRedemptionInline)
    date_hierarchy = "start_date"
    ordering = ("-start_date", "-pk")

    fieldsets = (
        (
            "Member",
            {
                "fields": ("user",),
                "description": "Search by name, username, or account number.",
            },
        ),
        (
            "Deposit recording",
            {
                "fields": (
                    "receipt_number",
                    "principal_amount",
                    "transaction_date",
                    "start_date",
                    "maturity_date",
                ),
                "description": "Receipt reference, amount fixed, transaction date, and FD term dates.",
            },
        ),
        (
            "Interest & payout (member-visible)",
            {
                "fields": (
                    "interest_rate",
                    "interest_method",
                    "compounding_frequency",
                    "payout_structure_display",
                    "redeemable_monthly_interest",
                    "redeemable_balance_display",
                ),
                "description": (
                    "Enable “Redeemable monthly interest” for deposits that may move "
                    "calendar-month interest to Main Account before maturity (e.g. ~120M group)."
                ),
            },
        ),
        (
            "Tax (internal — not shown on member dashboard)",
            {
                "fields": ("tax_rate",),
                "description": "Applied to gross interest at withdrawal / internal calculations. Default 15%.",
            },
        ),
        (
            "Status & reference",
            {"fields": ("status", "deposit_id")},
        ),
        (
            "Optional policy & notes",
            {
                "classes": ("collapse",),
                "fields": (
                    "auto_renewal",
                    "minimum_lock_period_days",
                    "early_withdrawal_penalty",
                    "notes",
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    actions = (
        "action_mark_matured",
        "action_mark_withdrawn",
        "action_mark_active",
        "action_mark_cancelled",
        "action_enable_monthly_redeem",
        "action_disable_monthly_redeem",
    )

    def member_display(self, obj: GWCFixedDeposit) -> str:
        u = obj.user
        name = u.get_full_name().strip()
        return name or u.get_username()

    member_display.short_description = "Member"
    member_display.admin_order_field = "user__first_name"

    def redeemable_balance_display(self, obj: GWCFixedDeposit) -> str:
        if not obj.pk:
            return "—"
        if not obj.redeemable_monthly_interest:
            return format_html('<span style="color:#94a3b8;">Off</span>')
        ledger = monthly_interest_ledger(obj)
        redeemable = f"{float(ledger['redeemable']):,.0f}"
        earned = f"{float(ledger['total_earned']):,.0f}"
        redeemed = f"{float(ledger['total_redeemed']):,.0f}"
        return format_html(
            "<span style='color:#166534;font-weight:600;'>UGX {}</span>"
            "<br><small style='color:#64748b;'>Earned {} · Transferred {}</small>",
            redeemable,
            earned,
            redeemed,
        )

    redeemable_balance_display.short_description = "Redeemable interest"

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        today = timezone.localdate()
        initial.setdefault("interest_rate", Decimal("25"))
        initial.setdefault("tax_rate", Decimal("15"))
        initial.setdefault(
            "compounding_frequency", GWCFixedDeposit.CompoundingFrequency.ANNUALLY
        )
        initial.setdefault("interest_method", GWCFixedDeposit.InterestMethod.COMPOUND)
        initial.setdefault("payout_structure_display", "At maturity")
        initial.setdefault("transaction_date", today)
        initial.setdefault("start_date", today)
        return initial

    @admin.action(description="Mark selected as Matured")
    def action_mark_matured(self, request, queryset):
        updated = queryset.update(status=GWCFixedDeposit.Status.MATURED)
        self.message_user(request, f"{updated} deposit(s) marked as Matured.", messages.SUCCESS)

    @admin.action(description="Mark selected as Withdrawn")
    def action_mark_withdrawn(self, request, queryset):
        updated = queryset.update(status=GWCFixedDeposit.Status.WITHDRAWN)
        self.message_user(request, f"{updated} deposit(s) marked as Withdrawn.", messages.SUCCESS)

    @admin.action(description="Mark selected as Active")
    def action_mark_active(self, request, queryset):
        updated = queryset.update(status=GWCFixedDeposit.Status.ACTIVE)
        self.message_user(request, f"{updated} deposit(s) marked as Active.", messages.SUCCESS)

    @admin.action(description="Mark selected as Cancelled")
    def action_mark_cancelled(self, request, queryset):
        updated = queryset.update(status=GWCFixedDeposit.Status.CANCELLED)
        self.message_user(request, f"{updated} deposit(s) marked as Cancelled.", messages.WARNING)

    @admin.action(description="Enable redeemable monthly interest")
    def action_enable_monthly_redeem(self, request, queryset):
        count = 0
        for deposit in queryset:
            deposit.redeemable_monthly_interest = True
            deposit.save()
            count += 1
        self.message_user(
            request,
            f"Enabled monthly interest redemption on {count} deposit(s).",
            messages.SUCCESS,
        )

    @admin.action(description="Disable redeemable monthly interest")
    def action_disable_monthly_redeem(self, request, queryset):
        updated = queryset.update(redeemable_monthly_interest=False)
        self.message_user(
            request,
            f"Disabled monthly interest redemption on {updated} deposit(s).",
            messages.WARNING,
        )


@admin.register(GWCInterestRedemption)
class GWCInterestRedemptionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "deposit",
        "amount",
        "redeemed_at",
        "created_by",
        "main_account_transaction",
    )
    list_filter = ("redeemed_at",)
    search_fields = (
        "deposit__deposit_id",
        "deposit__user__username",
        "deposit__user__first_name",
        "deposit__user__last_name",
        "notes",
    )
    autocomplete_fields = ("deposit", "created_by", "main_account_transaction")
    readonly_fields = (
        "deposit",
        "amount",
        "redeemed_at",
        "notes",
        "main_account_transaction",
        "created_by",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
