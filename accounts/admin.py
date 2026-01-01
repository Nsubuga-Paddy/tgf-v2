from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.utils import timezone
from .models import UserProfile, Project, AccountNumberCounter, WithdrawalRequest, MESUInterest
from core.admin_base import ExportableAdminMixin


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = (
        'photo', 'whatsapp_number', 'national_id', 'birthdate', 
        'address', 'bio', 'account_number', 'is_verified', 'is_admin',
        'projects'
    )
    readonly_fields = ('account_number', 'created_at', 'updated_at')
    filter_horizontal = ('projects',)
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Ensure the projects field uses the proper ManyToMany widget
        if 'projects' in form.base_fields:
            form.base_fields['projects'].widget.can_add_related = True
            form.base_fields['projects'].widget.can_change_related = True
            form.base_fields['projects'].widget.can_delete_related = False
        return form


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_account_number', 'get_verification_status')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'profile__is_verified', 'profile__is_admin')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'profile__account_number')
    ordering = ('username',)
    
    def get_account_number(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.account_number
        return 'No Profile'
    get_account_number.short_description = 'Account Number'
    
    def get_verification_status(self, obj):
        if hasattr(obj, 'profile'):
            if obj.profile.is_verified:
                return '✅ Verified'
            return '⏳ Pending'
        return '❌ No Profile'
    get_verification_status.short_description = 'Status'


@admin.register(UserProfile)
class UserProfileAdmin(ExportableAdminMixin, admin.ModelAdmin):
    list_display = ('user', 'account_number', 'whatsapp_number', 'is_verified', 'is_admin', 'get_projects', 'created_at')
    list_filter = ('is_verified', 'is_admin', 'projects', 'created_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'account_number', 'whatsapp_number')
    readonly_fields = ('account_number', 'created_at', 'updated_at')
    filter_horizontal = ('projects',)
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'photo', 'account_number')
        }),
        ('Personal Details', {
            'fields': ('whatsapp_number', 'national_id', 'birthdate', 'address', 'bio')
        }),
        ('Bank Account Information', {
            'fields': ('bank_name', 'bank_account_number', 'bank_account_name'),
            'description': 'Bank account details for withdrawals and deposits'
        }),
        ('Status & Permissions', {
            'fields': ('is_verified', 'is_admin', 'projects')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user').prefetch_related('projects')
    
    def get_projects(self, obj):
        """Display projects as a comma-separated list"""
        projects = obj.projects.all()
        if projects:
            return ', '.join([project.name for project in projects])
        return 'No projects'
    get_projects.short_description = 'Projects'
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Ensure the projects field uses the proper ManyToMany widget
        if 'projects' in form.base_fields:
            form.base_fields['projects'].widget.can_add_related = True
            form.base_fields['projects'].widget.can_change_related = True
            form.base_fields['projects'].widget.can_delete_related = False
        return form


@admin.register(Project)
class ProjectAdmin(ExportableAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'description', 'get_member_count')
    search_fields = ('name', 'description')
    
    def get_member_count(self, obj):
        return obj.members.count()
    get_member_count.short_description = 'Members'
    
    fieldsets = (
        ('Project Information', {
            'fields': ('name', 'description')
        }),
    )


@admin.register(AccountNumberCounter)
class AccountNumberCounterAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at')
    readonly_fields = ('created_at',)
    
    def has_add_permission(self, request):
        # Only allow one counter instance
        return not AccountNumberCounter.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of the counter
        return False


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(ExportableAdminMixin, admin.ModelAdmin):
    list_display = ('user_profile', 'amount', 'status_badge', 'bank_name', 'bank_account_name', 'requested_at', 'approved_at')
    list_filter = ('status', 'requested_at', 'approved_at')
    search_fields = ('user_profile__user__username', 'user_profile__user__first_name', 'user_profile__user__last_name', 
                     'bank_name', 'bank_account_number', 'bank_account_name')
    readonly_fields = ('requested_at', 'approved_at', 'completed_at')
    
    fieldsets = (
        ('Request Information', {
            'fields': ('user_profile', 'amount', 'status')
        }),
        ('Bank Account Details', {
            'fields': ('bank_name', 'bank_account_number', 'bank_account_name')
        }),
        ('Admin Processing', {
            'fields': ('admin_notes', 'approved_by')
        }),
        ('Timestamps', {
            'fields': ('requested_at', 'approved_at', 'completed_at'),
            'classes': ('collapse',)
        })
    )
    
    def status_badge(self, obj):
        """Display status as colored badge"""
        colors = {
            'pending': 'orange',
            'approved': 'blue',
            'rejected': 'red',
            'completed': 'green'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user_profile', 'user_profile__user', 'approved_by')
    
    actions = ['approve_withdrawals', 'reject_withdrawals']
    
    def approve_withdrawals(self, request, queryset):
        """Approve selected withdrawal requests and deduct amount"""
        from savings_52_weeks.models import SavingsTransaction
        
        count = 0
        for withdrawal in queryset.filter(status='pending'):
            try:
                # Create withdrawal transaction
                SavingsTransaction.objects.create(
                    user_profile=withdrawal.user_profile,
                    amount=withdrawal.amount,
                    transaction_type='withdrawal',
                    receipt_number=f'WDR-{withdrawal.id}-{timezone.now().strftime("%Y%m%d")}',
                    transaction_date=timezone.localdate()
                )
                
                withdrawal.status = 'approved'
                withdrawal.approved_by = request.user
                withdrawal.approved_at = timezone.now()
                withdrawal.save()
                count += 1
            except Exception as e:
                self.message_user(request, f'Error processing withdrawal {withdrawal.id}: {str(e)}', level='ERROR')
        
        self.message_user(request, f'{count} withdrawal request(s) approved and processed.')
    approve_withdrawals.short_description = 'Approve selected withdrawals'
    
    def reject_withdrawals(self, request, queryset):
        """Reject selected withdrawal requests"""
        count = queryset.filter(status='pending').update(
            status='rejected',
            approved_by=request.user,
            approved_at=timezone.now()
        )
        self.message_user(request, f'{count} withdrawal request(s) rejected.')
    reject_withdrawals.short_description = 'Reject selected withdrawals'


@admin.register(MESUInterest)
class MESUInterestAdmin(ExportableAdminMixin, admin.ModelAdmin):
    list_display = ('user_profile', 'shares_requested', 'total_amount', 'status_badge', 'requested_at', 'approved_at')
    list_filter = ('status', 'requested_at', 'approved_at')
    search_fields = ('user_profile__user__username', 'user_profile__user__first_name', 'user_profile__user__last_name')
    readonly_fields = ('total_amount', 'requested_at', 'approved_at', 'completed_at')
    
    fieldsets = (
        ('Request Information', {
            'fields': ('user_profile', 'shares_requested', 'total_amount', 'status')
        }),
        ('Admin Processing', {
            'fields': ('admin_notes', 'approved_by')
        }),
        ('Timestamps', {
            'fields': ('requested_at', 'approved_at', 'completed_at'),
            'classes': ('collapse',)
        })
    )
    
    def status_badge(self, obj):
        """Display status as colored badge"""
        colors = {
            'pending': 'orange',
            'approved': 'blue',
            'rejected': 'red',
            'completed': 'green'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user_profile', 'user_profile__user', 'approved_by')
    
    actions = ['approve_mesu_requests', 'reject_mesu_requests']
    
    def approve_mesu_requests(self, request, queryset):
        """Approve selected MESU interest requests and deduct amount"""
        from savings_52_weeks.models import SavingsTransaction
        
        count = 0
        for mesu in queryset.filter(status='pending'):
            try:
                # Create withdrawal transaction for MESU purchase
                SavingsTransaction.objects.create(
                    user_profile=mesu.user_profile,
                    amount=mesu.total_amount,
                    transaction_type='withdrawal',
                    receipt_number=f'MESU-{mesu.id}-{timezone.now().strftime("%Y%m%d")}',
                    transaction_date=timezone.localdate()
                )
                
                mesu.status = 'approved'
                mesu.approved_by = request.user
                mesu.approved_at = timezone.now()
                mesu.save()
                count += 1
            except Exception as e:
                self.message_user(request, f'Error processing MESU request {mesu.id}: {str(e)}', level='ERROR')
        
        self.message_user(request, f'{count} MESU interest request(s) approved and processed.')
    approve_mesu_requests.short_description = 'Approve selected MESU requests'
    
    def reject_mesu_requests(self, request, queryset):
        """Reject selected MESU interest requests"""
        count = queryset.filter(status='pending').update(
            status='rejected',
            approved_by=request.user,
            approved_at=timezone.now()
        )
        self.message_user(request, f'{count} MESU interest request(s) rejected.')
    reject_mesu_requests.short_description = 'Reject selected MESU requests'


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
