from django.contrib import admin
from django.db.models import Sum
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import (
    Farm, ManagementFeeTier, InvestmentPackage, 
    UserFarmAccount, PackagePurchase, Payment, CGFActionRequest
)
from core.admin_base import ExportableAdminMixin

@admin.register(Farm)
class FarmAdmin(ExportableAdminMixin, admin.ModelAdmin):
    list_display = ['name', 'location', 'capacity_display', 'current_goats_display', 'available_capacity_display', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'location']
    
    def capacity_display(self, obj):
        percentage = obj.capacity_percentage
        color = 'red' if percentage > 80 else 'orange' if percentage > 60 else 'green'
        return format_html(
            '<div style="color: {};">{}/{} ({}%)</div>',
            color, obj.current_goats, obj.total_capacity, round(percentage, 1)
        )
    capacity_display.short_description = 'Capacity Usage'
    
    def current_goats_display(self, obj):
        return obj.current_goats
    current_goats_display.short_description = 'Current Goats'
    
    def available_capacity_display(self, obj):
        return obj.available_capacity
    available_capacity_display.short_description = 'Available Space'

@admin.register(ManagementFeeTier)
class ManagementFeeTierAdmin(ExportableAdminMixin, admin.ModelAdmin):
    list_display = ['goat_range', 'annual_fee_display']
    ordering = ['min_goats']
    
    def goat_range(self, obj):
        return f"{obj.min_goats} - {obj.max_goats} goats"
    
    def annual_fee_display(self, obj):
        return f"UGX {float(obj.annual_fee):,.0f}"
    annual_fee_display.short_description = 'Annual Fee'

@admin.register(InvestmentPackage)
class InvestmentPackageAdmin(ExportableAdminMixin, admin.ModelAdmin):
    list_display = ['name', 'goat_count', 'kids_per_goat', 'goat_cost_display', 'management_fee_display', 'total_cost_display', 'is_active']
    list_filter = ['is_active', 'management_fee_tier']
    
    def goat_cost_display(self, obj):
        return f"UGX {float(obj.goat_cost):,.0f}"
    goat_cost_display.short_description = 'Goat Cost'
    
    def management_fee_display(self, obj):
        return f"UGX {float(obj.management_fee):,.0f}"
    management_fee_display.short_description = 'Management Fee'
    
    def total_cost_display(self, obj):
        return f"UGX {float(obj.total_cost):,.0f}"
    total_cost_display.short_description = 'Total Cost'

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ['created_at', 'receipt_prefix', 'receipt_number']
    fields = ['receipt_prefix', 'receipt_suffix', 'receipt_number', 'amount', 'payment_method', 'payment_date', 'created_at']

@admin.register(PackagePurchase)
class PackagePurchaseAdmin(ExportableAdminMixin, admin.ModelAdmin):
    list_display = [
        'user', 'farm', 'package', 'total_amount_display',
        'amount_paid_display', 'balance_due_display', 'payment_status',
        'goats_status', 'purchase_date'
    ]
    list_editable = ['purchase_date']
    list_filter = ['status', 'farm', 'package']
    search_fields = ['user__user__username', 'user__user__first_name', 'user__user__last_name']
    inlines = [PaymentInline]
    actions = ['allocate_goats_action']

    def _fmt_currency(self, value):
        """Return a formatted UGX string for a numeric value (Decimal/float/int)."""
        try:
            # Convert to float then format with thousands separator, no decimals
            formatted = f"{float(value):,.0f}"
        except Exception:
            # Fallback: show raw value as string
            formatted = str(value)
        return f"UGX {formatted}"

    def total_amount_display(self, obj):
        return self._fmt_currency(obj.total_amount)
    total_amount_display.short_description = 'Total Amount'
    total_amount_display.admin_order_field = 'total_amount'

    def amount_paid_display(self, obj):
        return self._fmt_currency(obj.amount_paid)
    amount_paid_display.short_description = 'Amount Paid'
    amount_paid_display.admin_order_field = 'amount_paid'

    def balance_due_display(self, obj):
        balance = obj.balance_due
        # Format as string first to avoid format_html applying numeric format on non-numeric
        formatted_balance = f"{float(balance):,.0f}" if balance is not None else "0"
        color = 'green' if balance == 0 else 'orange' if obj.amount_paid > 0 else 'red'
        return format_html(
            '<span style="color: {};">UGX {}</span>',
            color, formatted_balance
        )
    balance_due_display.short_description = 'Balance Due'
    balance_due_display.admin_order_field = 'total_amount'  # or a more appropriate field

    def payment_status(self, obj):
        colors = {
            'pending': 'red',
            'partial': 'orange',
            'paid': 'green',
            'allocated': 'blue'
        }
        # get_status_display() returns a safe string sometimes; we only insert it as text
        return format_html(
            '<span style="color: {};">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    payment_status.short_description = 'Payment Status'
    payment_status.admin_order_field = 'status'

    def goats_status(self, obj):
        if obj.goats_allocated > 0:
            # both values are integers, format to string first
            s = f"{obj.goats_allocated}/{obj.package.goat_count} goats allocated"
            return format_html('<span style="color: green;">{}</span>', s)
        elif obj.is_fully_paid:
            return format_html('<span style="color: orange;">Ready for allocation</span>')
        else:
            return format_html('<span style="color: red;">Awaiting payment</span>')
    goats_status.short_description = 'Goat Status'

    def allocate_goats_action(self, request, queryset):
        count = 0
        for purchase in queryset:
            if purchase.is_fully_paid and purchase.goats_allocated == 0:
                if purchase.allocate_goats_to_accounts():
                    count += 1

        self.message_user(request, f'Successfully allocated goats for {count} purchases.')
    allocate_goats_action.short_description = 'Allocate goats to accounts'

@admin.register(UserFarmAccount)
class UserFarmAccountAdmin(ExportableAdminMixin, admin.ModelAdmin):
    list_display = ['user_display', 'farm', 'current_goats', 'expected_kids', 'is_active', 'created_at']
    list_filter = ['farm', 'is_active', 'created_at']
    search_fields = ['user__user__username', 'user__user__first_name', 'user__user__last_name', 'user__account_number']
    ordering = ['farm', 'user']
    list_editable = ['current_goats', 'expected_kids', 'is_active', 'created_at']
    
    def user_display(self, obj):
        """Display user name and their system account number"""
        account_num = obj.user.account_number or "No Account#"
        return format_html(
            '<strong>{}</strong><br><small style="color: #666;">Account: {}</small>',
            obj.user.display_name, account_num
        )
    user_display.short_description = 'User & Account'
    user_display.admin_order_field = 'user'

@admin.register(Payment)
class PaymentAdmin(ExportableAdminMixin, admin.ModelAdmin):
    list_display = ['receipt_number', 'purchase_info', 'amount_display', 'payment_method', 'payment_date']
    list_filter = ['payment_method', 'payment_date']
    search_fields = ['receipt_number', 'purchase__user__user__username']
    readonly_fields = ['created_at', 'receipt_prefix', 'receipt_number']
    fieldsets = (
        ('Payment Information', {
            'fields': ('purchase', 'amount', 'payment_method', 'payment_date')
        }),
        ('Receipt Details', {
            'fields': ('receipt_prefix', 'receipt_suffix', 'receipt_number'),
            'description': 'The prefix is auto-generated (RCPT-YYYYMMDD). Enter only the suffix from your receipt book (e.g., DCF001)'
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at'),
            'classes': ('collapse',)
        })
    )
    
    def purchase_info(self, obj):
        return f"{obj.purchase.user.display_name} - {obj.purchase.package.name}"
    purchase_info.short_description = 'Purchase'
    
    def amount_display(self, obj):
        return f"UGX {float(obj.amount):,.0f}"
    amount_display.short_description = 'Amount'
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'receipt_suffix' in form.base_fields:
            # Add example suffix as placeholder
            form.base_fields['receipt_suffix'].widget.attrs.update({
                'placeholder': 'DCF001, DCF002, etc.',
                'style': 'font-family: monospace; font-size: 14px;'
            })
        return form


@admin.register(CGFActionRequest)
class CGFActionRequestAdmin(ExportableAdminMixin, admin.ModelAdmin):
    list_display = ['user_profile', 'request_type_display', 'goats_count', 'cash_value_display', 'notes_preview', 'status', 'created_at', 'link_to_profile']
    list_filter = ['request_type', 'status', 'created_at']
    list_editable = ['status']
    search_fields = ['user_profile__user__username', 'user_profile__user__first_name', 'user_profile__user__last_name', 'user_profile__account_number', 'notes']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    fieldsets = (
        ('Request Details', {
            'fields': ('user_profile', 'request_type', 'goats_count', 'notes', 'status'),
            'description': 'Review the CGF action request (Sell & Cash Out, Take Goats, or Transfer). Update status to approve, reject, or mark as processed.'
        }),
        ('Admin Action', {
            'fields': ('admin_notes', 'processed_at'),
            'description': 'Add notes (e.g. pickup date, transfer details, payment ref) and set processed date when complete.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def request_type_display(self, obj):
        return obj.get_request_type_display()
    request_type_display.short_description = 'Action Type'
    request_type_display.admin_order_field = 'request_type'

    def cash_value_display(self, obj):
        if obj.request_type == 'sell_cash_out' and obj.goats_count:
            return f'UGX {obj.cash_value:,.0f}'
        return '—'
    cash_value_display.short_description = 'Cash Value (Sell)'

    def notes_preview(self, obj):
        if obj.notes:
            return obj.notes[:40] + '...' if len(obj.notes) > 40 else obj.notes
        return '—'
    notes_preview.short_description = 'User Notes'

    def link_to_profile(self, obj):
        from django.urls import reverse
        url = reverse('admin:accounts_userprofile_change', args=[obj.user_profile.id])
        return format_html('<a href="{}">View Profile</a>', url)
    link_to_profile.short_description = 'User'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user_profile__user')