from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, Project, AccountNumberCounter, WithdrawalRequest, GWCContribution, MESUInterest
from core.admin_base import ExportableAdminMixin


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = (
        'photo', 'whatsapp_number', 'national_id', 'birthdate', 
        'address', 'bio', 'account_number', 'bank_name', 'bank_account_number', 
        'bank_account_name', 'is_verified', 'is_admin', 'projects'
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
    list_display = ('user', 'account_number', 'whatsapp_number', 'get_bank_info', 'is_verified', 'is_admin', 'get_projects', 'created_at')
    list_filter = ('is_verified', 'is_admin', 'projects', 'created_at', 'bank_name')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'account_number', 'whatsapp_number', 'bank_name', 'bank_account_number', 'bank_account_name')
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
            'description': 'Bank account details used for withdrawals and payments. Admin will use these to send money to users.'
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
    
    def get_bank_info(self, obj):
        """Display bank account information"""
        if obj.bank_name and obj.bank_account_number:
            return f"{obj.bank_name} - {obj.bank_account_number}"
        return 'Not provided'
    get_bank_info.short_description = 'Bank Account'
    
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


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(ExportableAdminMixin, admin.ModelAdmin):
    list_display = ('user_profile', 'amount', 'status', 'created_at', 'get_bank_info')
    list_filter = ('status', 'created_at')
    search_fields = ('user_profile__user__username', 'user_profile__user__first_name', 'user_profile__user__last_name', 'user_profile__account_number')
    readonly_fields = ('created_at', 'updated_at', 'get_bank_info')
    fieldsets = (
        ('Request Information', {
            'fields': ('user_profile', 'amount', 'reason', 'status')
        }),
        ('Bank Account Details', {
            'fields': ('get_bank_info',),
            'description': 'Bank account information from user profile'
        }),
        ('Admin Actions', {
            'fields': ('admin_notes', 'processed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_bank_info(self, obj):
        """Display bank account information from user profile"""
        profile = obj.user_profile
        if profile.bank_name and profile.bank_account_number:
            account_name = profile.bank_account_name or 'N/A'
            return f"{profile.bank_name} | {profile.bank_account_number} | {account_name}"
        return 'Not provided'
    get_bank_info.short_description = 'Bank Account'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user_profile__user')


@admin.register(GWCContribution)
class GWCContributionAdmin(ExportableAdminMixin, admin.ModelAdmin):
    list_display = ('user_profile', 'amount', 'group_type', 'status', 'created_at')
    list_filter = ('status', 'group_type', 'created_at')
    search_fields = ('user_profile__user__username', 'user_profile__user__first_name', 'user_profile__user__last_name', 'user_profile__account_number')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Contribution Information', {
            'fields': ('user_profile', 'amount', 'group_type', 'status')
        }),
        ('Admin Actions', {
            'fields': ('admin_notes', 'processed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user_profile__user')


@admin.register(MESUInterest)
class MESUInterestAdmin(ExportableAdminMixin, admin.ModelAdmin):
    list_display = ('user_profile', 'investment_amount', 'number_of_shares', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user_profile__user__username', 'user_profile__user__first_name', 'user_profile__user__last_name', 'user_profile__account_number')
    readonly_fields = ('number_of_shares', 'created_at', 'updated_at')
    fieldsets = (
        ('Investment Information', {
            'fields': ('user_profile', 'investment_amount', 'number_of_shares', 'notes', 'status')
        }),
        ('Admin Actions', {
            'fields': ('admin_notes', 'processed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user_profile__user')
