"""
Django admin for GWC fixed deposits — streamlined recording workflow.
"""
from __future__ import annotations

from decimal import Decimal

from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import GWCDepositActivity, GWCFixedDeposit

User = get_user_model()


class GWCDepositActivityInline(admin.TabularInline):
    """Optional lines that appear on the member Activity panel (e.g. interest accrual)."""

    model = GWCDepositActivity
    extra = 0
    fields = ("timestamp", "activity_type", "description", "amount")
    ordering = ("-timestamp",)
    classes = ("collapse",)


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
        "status",
    )
    list_filter = ("status", "start_date", "interest_method")
    search_fields = (
        "deposit_id",
        "receipt_number",
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
    )
    readonly_fields = ("deposit_id", "created_at", "updated_at")
    inlines = (GWCDepositActivityInline,)
    date_hierarchy = "start_date"
    ordering = ("-start_date", "-pk")

    fieldsets = (
        (
            "Member",
            {
                "fields": ("user",),
                "description": "Choose the member (full name shown in the dropdown).",
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
    )

    def member_display(self, obj: GWCFixedDeposit) -> str:
        u = obj.user
        name = u.get_full_name().strip()
        return name or u.get_username()

    member_display.short_description = "Member"
    member_display.admin_order_field = "user__first_name"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "user":
            kwargs["queryset"] = User.objects.order_by(
                "first_name", "last_name", "username"
            )
        formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "user":

            def label(u):
                name = u.get_full_name().strip()
                return f"{name} ({u.get_username()})" if name else u.get_username()

            formfield.label_from_instance = label
        return formfield

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
