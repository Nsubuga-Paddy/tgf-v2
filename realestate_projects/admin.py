from django.contrib import admin

from .models import (
    RealEstateProject,
    RealEstateProjectInterest,
    RealEstateProjectJoinRequest,
    RealEstateProjectTransaction,
    RealEstateProjectActionRequest,
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
    filter_horizontal = ("allowed_members",)


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
    search_fields = ("project__name", "user__username", "user__first_name", "user__last_name")


@admin.register(RealEstateProjectInterest)
class RealEstateProjectInterestAdmin(admin.ModelAdmin):
    list_display = ("project", "user", "created_at")
    list_filter = ("created_at",)
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
        "created_at",
        "processed_at",
    )
    list_filter = ("action_type", "status", "created_at")
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
