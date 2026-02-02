
from decimal import Decimal
from django.contrib import admin
from django.db.models import Sum, Window, F, Case, When, DecimalField, Value
from django.utils import timezone

from .models import SavingsTransaction, Investment
from core.admin_base import ExportableAdminMixin


@admin.register(SavingsTransaction)
class SavingsTransactionAdmin(ExportableAdminMixin, admin.ModelAdmin):
    list_display = (
        'id', 'user_profile', 'amount', 'transaction_type', 'receipt_number',
        'transaction_date',

        # Summary columns
        'total_deposit_running',        # per-row running total
        'covered_weeks_display',
        'balance_bf_display',
        'next_week_display',

        'created_at',
    )
    list_filter = (
        'transaction_type', 'transaction_date',
        'created_at', 'user_profile__is_verified'
    )
    search_fields = (
        'user_profile__user__username', 'user_profile__user__first_name', 'user_profile__user__last_name',
        'user_profile__account_number', 'receipt_number'
    )
    readonly_fields = ('created_at', 'updated_at', 'fully_covered_weeks', 'remaining_balance', 'cumulative_total', 'next_week',)
    date_hierarchy = 'transaction_date'
    ordering = ('-transaction_date', '-created_at')

    fieldsets = (
        ('Transaction Details', {
            'fields': ('user_profile', 'amount', 'transaction_type', 'receipt_number')
        }),
        ('Timing', {
            'fields': ('transaction_date',)
        }),
        ('Calculated Results', {
            'fields': ('fully_covered_weeks', 'remaining_balance', 'cumulative_total', 'next_week'),
            'description': 'These fields are automatically calculated when the transaction is saved.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def get_readonly_fields(self, request, obj=None):
        """Ensure calculated fields are always read-only."""
        ro = list(super().get_readonly_fields(request, obj))
        ro.extend(['fully_covered_weeks', 'remaining_balance', 'cumulative_total', 'next_week'])
        return ro

    def get_queryset(self, request):
        """
        Annotate each row with a running sum (deposits - withdrawals - GWC contributions) for that user_profile,
        ordered by (transaction_date, created_at, id) to keep it deterministic.
        Requires Postgres, MySQL 8+, or SQLite 3.25+ (window functions).
        This matches the calculation used in the member dashboard.
        """
        qs = super().get_queryset(request).select_related('user_profile', 'user_profile__user')
        # Calculate net: deposits add, withdrawals and GWC contributions subtract
        net_amount = Case(
            When(transaction_type='deposit', then=F('amount')),
            When(transaction_type__in=('withdrawal', 'gwc_contribution'), then=-F('amount')),
            default=Value(0),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
        return qs.annotate(
            running_total_deposit=Window(
                expression=Sum(net_amount),
                partition_by=[F('user_profile_id')],
                order_by=[F('transaction_date').asc(), F('created_at').asc(), F('id').asc()],
            )
        )

    # ---------- Columns ----------

    def total_deposit_running(self, obj):
        """
        Cumulative net balance up to *this* row for this user (deposits - withdrawals - GWC contributions).
        This matches the calculation used in the member dashboard.
        """
        val = getattr(obj, 'running_total_deposit', None)
        if val is None:
            return '—'
        # Format with proper sign indication
        if val < 0:
            return f"<span style='color: #dc2626;'>UGX{val:,.0f}</span>"
        return f"UGX{val:,.0f}"
    total_deposit_running.short_description = "Net Balance (Running)"
    total_deposit_running.allow_tags = True

    def covered_weeks_display(self, obj):
        """
        Render like: 'Week 1, Week 2' (no amounts/checkmarks).
        Uses only fully covered weeks from THIS transaction.
        """
        if not obj.fully_covered_weeks:
            return "—"

        weeks = []
        for item in obj.fully_covered_weeks:
            if item.get('fully_covered', False):
                try:
                    weeks.append(int(item.get('week')))
                except Exception:
                    continue

        if not weeks:
            return "—"

        weeks = sorted(set(weeks))
        return ", ".join(f"Week {w}" for w in weeks)
    covered_weeks_display.short_description = "Covered Weeks"

    
    def balance_bf_display(self, obj):
        """
        Balance brought forward (unallocated remainder after this allocation).
        For withdrawals/GWC, shows 0. For deposits, shows remaining_balance.
        This matches the logic used in the member dashboard.
        """
        # If this is a withdrawal or GWC contribution, balance forward is 0
        if obj.transaction_type in ('withdrawal', 'gwc_contribution'):
            return "UGX 0"
        
        # For deposits, show the remaining balance (unallocated for weeks)
        try:
            balance = obj.remaining_balance or Decimal('0.00')
            return f"UGX{float(balance):,.0f}"
        except Exception:
            return str(obj.remaining_balance) if obj.remaining_balance else "UGX 0"
    balance_bf_display.short_description = "Balance BF"


    def next_week_display(self, obj):
        """
        Show 'Week N' or 'Complete' when all 52 are done.
        For withdrawals/GWC contributions, shows 'N/A' since they don't affect week coverage.
        """
        # Withdrawals and GWC contributions don't have week coverage
        if obj.transaction_type in ('withdrawal', 'gwc_contribution'):
            return "N/A"
        
        if obj.next_week and obj.next_week <= 52:
            return f"Week {obj.next_week}"
        return "Complete"
    next_week_display.short_description = "Next Week"



    # Convenience
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'user_profile' in form.base_fields:
            form.base_fields['user_profile'].widget.can_add_related = True
            form.base_fields['user_profile'].widget.can_change_related = True
        return form


@admin.register(Investment)
class InvestmentAdmin(ExportableAdminMixin, admin.ModelAdmin):
    list_display = (
        'id', 'user_profile', 'amount_invested', 'investment_type', 'interest_rate',
        'start_date', 'maturity_date', 'status', 'days_until_maturity', 'daily_interest', 'total_interest_expected'
    )
    list_filter = (
        'investment_type', 'status', 'start_date',
        'created_at', 'user_profile__is_verified'
    )
    search_fields = (
        'user_profile__user__username', 'user_profile__user__first_name', 'user_profile__user__last_name',
        'user_profile__account_number', 'notes'
    )
    readonly_fields = ('created_at', 'updated_at', 'total_interest_expected')
    date_hierarchy = 'start_date'
    ordering = ('-start_date', '-created_at')
    
    fieldsets = (
        ('Investment Details', {
            'fields': ('user_profile', 'amount_invested', 'investment_type', 'interest_rate')
        }),
        ('Timing', {
            'fields': ('start_date', 'maturity_months')
        }),
        ('Status & Notes', {
            'fields': ('status', 'notes')
        }),
        ('Calculated Fields', {
            'fields': ('total_interest_expected',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user_profile', 'user_profile__user'
        )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Make user_profile field more searchable
        if 'user_profile' in form.base_fields:
            form.base_fields['user_profile'].widget.can_add_related = True
            form.base_fields['user_profile'].widget.can_change_related = True
        return form

    def maturity_date(self, obj):
        """Display maturity date"""
        return obj.maturity_date
    maturity_date.short_description = "Maturity Date"

    def days_until_maturity(self, obj):
        """Display days until maturity with color coding"""
        days = obj.days_until_maturity
        if days < 0:
            return f"<span style='color: #dc2626; font-weight: bold;'>Matured ({abs(days)} days ago)</span>"
        elif days == 0:
            return f"<span style='color: #dc2626; font-weight: bold;'>Matures Today!</span>"
        elif days <= 7:
            return f"<span style='color: #ea580c; font-weight: bold;'>{days} days</span>"
        elif days <= 30:
            return f"<span style='color: #ca8a04; font-weight: bold;'>{days} days</span>"
        else:
            return f"<span style='color: #ca8a04; font-weight: bold;'>{days} days</span>"
    days_until_maturity.short_description = "Days to Maturity"
    days_until_maturity.allow_tags = True

    def daily_interest(self, obj):
        """Display daily interest earned with color coding"""
        if obj.status == 'matured':
            return f"<span style='color: #6b7280; font-weight: bold;'>—</span>"
        
        daily_int = obj.interest_earned_today
        if daily_int > 0:
            return f"<span style='color: #059669; font-weight: bold;'>UGX {daily_int:,.2f}</span>"
        else:
            return f"<span style='color: #6b7280; font-weight: bold;'>UGX 0.00</span>"
    daily_interest.short_description = "Daily Interest"
    daily_interest.allow_tags = True
    
    actions = ['check_maturity_status', 'mark_as_fixed', 'mark_as_matured', 'calculate_interest']
    
    def check_maturity_status(self, request, queryset):
        """Check and update maturity status for selected investments"""
        matured_count = 0
        for investment in queryset:
            if investment.check_and_update_status():
                matured_count += 1
        
        if matured_count > 0:
            self.message_user(request, f'{matured_count} investments have matured and been updated automatically.')
        else:
            self.message_user(request, 'No investments have matured yet.')
    check_maturity_status.short_description = "Check maturity status for selected investments"
    
    def mark_as_fixed(self, request, queryset):
        """Mark selected investments as fixed"""
        updated = queryset.update(status='fixed')
        self.message_user(request, f'{updated} investments marked as fixed.')
    mark_as_fixed.short_description = "Mark selected investments as fixed"
    
    def mark_as_matured(self, request, queryset):
        """Mark selected investments as matured and create deposit transactions for interest earned"""
        count = 0
        for investment in queryset:
            if investment.status != 'matured':
                # Use check_and_update_status to ensure transaction is created
                investment.check_and_update_status()
                if investment.status == 'matured':
                    count += 1
        self.message_user(request, f'{count} investments marked as matured. Interest deposit transactions created automatically.')
    mark_as_matured.short_description = "Mark selected investments as matured"
    
    def calculate_interest(self, request, queryset):
        """Calculate interest for selected investments"""
        for investment in queryset:
            # This will trigger the property calculations
            investment.total_interest_expected
            investment.interest_gained_so_far
        self.message_user(request, f'Interest calculated for {queryset.count()} investments.')
    calculate_interest.short_description = "Calculate interest for selected investments"

    def show_daily_interest_summary(self, request, queryset):
        """Show daily interest summary for selected investments"""
        if not queryset.exists():
            self.message_user(request, "No investments selected.")
            return
        
        # Get daily interest summary for today
        summary = Investment.get_daily_interest_summary()
        
        # Calculate summary for selected investments
        selected_daily_total = sum(inv.interest_earned_today for inv in queryset if inv.status == 'fixed')
        selected_total_earned = sum(inv.interest_gained_so_far for inv in queryset)
        
        message = f"""
        <h3>Daily Interest Summary</h3>
        <p><strong>Date:</strong> {summary['date']}</p>
        <p><strong>Selected Investments Daily Interest:</strong> UGX {selected_daily_total:,.2f}</p>
        <p><strong>Selected Investments Total Earned:</strong> UGX {selected_total_earned:,.2f}</p>
        <p><strong>All Active Investments Daily Interest:</strong> UGX {summary['daily_interest_total']:,.2f}</p>
        <p><strong>All Active Investments Total Earned:</strong> UGX {summary['total_interest_earned']:,.2f}</p>
        <p><strong>Active Investments Count:</strong> {summary['active_investments']}</p>
        """
        
        self.message_user(request, message, extra_tags='safe')
    show_daily_interest_summary.short_description = "Show daily interest summary"

    def changelist_view(self, request, extra_context=None):
        """Custom changelist view to show maturity alerts"""
        # Check for recently matured investments
        matured_investments = Investment.objects.filter(status='matured')
        today = timezone.now().date()
        
        # Find investments that matured today or recently
        recent_matured = []
        for investment in matured_investments:
            if (today - investment.maturity_date).days <= 7:  # Within last 7 days
                recent_matured.append(investment)
        
        if recent_matured:
            extra_context = extra_context or {}
            extra_context['recent_matured'] = recent_matured
            extra_context['show_maturity_alert'] = True
        
        return super().changelist_view(request, extra_context)


# Customize admin site
admin.site.site_header = "MCS Financial Services Administration"
admin.site.site_title = "MCS Admin"
admin.site.index_title = "Welcome to MCS Financial Services"
