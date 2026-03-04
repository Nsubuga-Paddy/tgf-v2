from django.contrib import admin

from .models import (
    RealEstateProject,
    RealEstateProjectInterest,
    RealEstateProjectJoinRequest,
    RealEstateProjectMembership,
    RealEstateProjectTransaction,
)


class RealEstateProjectMembershipInline(admin.TabularInline):
    model = RealEstateProjectMembership
    extra = 1


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
    inlines = [RealEstateProjectMembershipInline]


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
