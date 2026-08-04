from django.contrib import admin, messages

from .models import (
    RealEstateProject,
    RealEstateProjectInterest,
    RealEstateProjectJoinRequest,
    RealEstateProjectTransaction,
    RealEstateProjectActionRequest,
)
from .services import (
    process_refund_request,
    reject_refund_request,
    reverse_premature_refund_credit,
)


@admin.register(RealEstateProject)
class RealEstateProjectAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "location",
        "status",
        "start_date",
        "end_date",
        "show_in_sidebar",
    )
    list_filter = ("status", "show_in_sidebar", "start_date")
    search_fields = ("name", "location")
    autocomplete_fields = ("allowed_members",)


@admin.register(RealEstateProjectJoinRequest)
class RealEstateProjectJoinRequestAdmin(admin.ModelAdmin):
    list_display = (
        "project",
        "user",
        "status",
        "created_at",
        "decided_at",
        "decided_by",
    )
    list_filter = ("status", "created_at")
    autocomplete_fields = ("project", "user", "decided_by")
    search_fields = ("project__name", "user__username", "user__first_name", "user__last_name")


@admin.register(RealEstateProjectInterest)
class RealEstateProjectInterestAdmin(admin.ModelAdmin):
    list_display = ("project", "user", "created_at")
    list_filter = ("created_at",)
    autocomplete_fields = ("project", "user")
    search_fields = ("project__name", "user__username", "user__first_name", "user__last_name")


@admin.register(RealEstateProjectTransaction)
class RealEstateProjectTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "project",
        "user",
        "amount",
        "acquisition_quantity",
        "acquisition_unit",
        "balance_after",
        "payment_status",
        "transaction_date",
    )
    list_filter = ("payment_status", "transaction_date")
    autocomplete_fields = ("project", "user")
    search_fields = ("project__name", "user__username", "user__first_name", "user__last_name")


@admin.register(RealEstateProjectActionRequest)
class RealEstateProjectActionRequestAdmin(admin.ModelAdmin):
    list_display = (
        "project",
        "user_full_name",
        "phone_display",
        "bank_details_display",
        "action_type",
        "amount",
        "available_at_request",
        "status",
        "main_account_transaction",
        "created_at",
        "processed_at",
        "processed_by",
    )
    list_filter = ("action_type", "status", "created_at")
    autocomplete_fields = ("project", "user", "processed_by")
    readonly_fields = (
        "available_at_request",
        "realestate_transaction",
        "main_account_transaction",
        "processed_by",
        "processed_at",
        "created_at",
    )
    actions = (
        "action_approve_and_credit_refunds",
        "action_reject_refunds",
        "action_reverse_refund_credits",
    )
    search_fields = (
        "project__name",
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__profile__whatsapp_number",
        "user__profile__bank_name",
        "user__profile__bank_account_number",
        "user__profile__bank_account_name",
    )

    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        # Lock amount/type after credit. Status stays editable until credited so
        # approving from the change form can still post the Main Account credit.
        if obj and obj.action_type == RealEstateProjectActionRequest.ACTION_REFUND:
            if obj.main_account_transaction_id:
                readonly = list(dict.fromkeys([*readonly, "status", "amount", "action_type"]))
            elif obj.status != RealEstateProjectActionRequest.STATUS_PENDING:
                readonly = list(dict.fromkeys([*readonly, "amount", "action_type"]))
        return readonly

    def user_full_name(self, obj):
        user = obj.user
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        return full_name or user.get_username()
    user_full_name.short_description = "Full Name"
    user_full_name.admin_order_field = "user__last_name"

    def phone_display(self, obj):
        profile = getattr(obj.user, "profile", None)
        if profile and profile.whatsapp_number:
            return str(profile.whatsapp_number)
        return "—"
    phone_display.short_description = "Phone Number"

    def bank_details_display(self, obj):
        profile = getattr(obj.user, "profile", None)
        if not profile:
            return "—"

        details = []
        if profile.bank_name:
            details.append(profile.bank_name)
        if profile.bank_account_number:
            details.append(profile.bank_account_number)
        if profile.bank_account_name:
            details.append(profile.bank_account_name)

        return " | ".join(details) if details else "Not provided"
    bank_details_display.short_description = "Bank Account"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "user__profile", "project")

    def save_model(self, request, obj, form, change):
        """Approving/processing a refund from the change form credits Main Account."""
        should_credit = (
            obj.action_type == RealEstateProjectActionRequest.ACTION_REFUND
            and obj.status
            in {
                RealEstateProjectActionRequest.STATUS_APPROVED,
                RealEstateProjectActionRequest.STATUS_PROCESSED,
            }
            and not obj.main_account_transaction_id
        )
        if should_credit:
            # Keep row pending until process_refund_request posts the ledger entries.
            obj.status = RealEstateProjectActionRequest.STATUS_PENDING
            super().save_model(request, obj, form, change)
            try:
                process_refund_request(
                    obj,
                    admin=request.user,
                    admin_notes=obj.admin_notes or "Refund credited to Main Account",
                )
                self.message_user(
                    request,
                    "Refund approved and credited to the member's Main Account.",
                    level=messages.SUCCESS,
                )
            except Exception as exc:
                self.message_user(
                    request,
                    f"Refund was saved as Pending but not credited: {exc}",
                    level=messages.ERROR,
                )
            return
        super().save_model(request, obj, form, change)

    @admin.action(description="Approve selected refunds and credit Main Account")
    def action_approve_and_credit_refunds(self, request, queryset):
        done = 0
        for item in queryset.filter(action_type=RealEstateProjectActionRequest.ACTION_REFUND):
            if item.main_account_transaction_id:
                continue
            if item.status not in {
                RealEstateProjectActionRequest.STATUS_PENDING,
                RealEstateProjectActionRequest.STATUS_APPROVED,
            }:
                continue
            try:
                process_refund_request(
                    item,
                    admin=request.user,
                    admin_notes=item.admin_notes or "Refund credited to Main Account",
                )
                done += 1
            except Exception as exc:
                self.message_user(request, f"{item}: {exc}", level=messages.ERROR)
        if done:
            self.message_user(
                request,
                f"Approved and credited {done} refund(s) to Main Account. "
                "Members can now withdraw from Main Account.",
                level=messages.SUCCESS,
            )
        else:
            self.message_user(
                request,
                "No refunds were credited. Select Pending/Approved refunds that are not yet credited.",
                level=messages.WARNING,
            )

    @admin.action(description="Reject selected pending/approved refunds (no credit yet)")
    def action_reject_refunds(self, request, queryset):
        done = 0
        for item in queryset.filter(
            action_type=RealEstateProjectActionRequest.ACTION_REFUND,
            status__in=[
                RealEstateProjectActionRequest.STATUS_PENDING,
                RealEstateProjectActionRequest.STATUS_APPROVED,
            ],
            main_account_transaction__isnull=True,
        ):
            try:
                reject_refund_request(
                    item,
                    admin=request.user,
                    admin_notes=item.admin_notes or "Refund request rejected by Administrator",
                )
                done += 1
            except Exception as exc:
                self.message_user(request, f"{item}: {exc}", level=messages.ERROR)
        if done:
            self.message_user(
                request,
                f"Rejected {done} refund request(s).",
                level=messages.SUCCESS,
            )

    @admin.action(description="Reverse Main Account refund credits (return request to Pending/held)")
    def action_reverse_refund_credits(self, request, queryset):
        done = 0
        for item in queryset.filter(
            action_type=RealEstateProjectActionRequest.ACTION_REFUND,
            main_account_transaction__isnull=False,
        ):
            try:
                reverse_premature_refund_credit(
                    item,
                    admin=request.user,
                    admin_notes="Main Account refund credit reversed. Refund held pending approval.",
                )
                done += 1
            except Exception as exc:
                self.message_user(request, f"{item}: {exc}", level=messages.ERROR)
        if done:
            self.message_user(
                request,
                f"Reversed {done} refund credit(s). Amounts are held again until approval.",
                level=messages.SUCCESS,
            )
