from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, Project, AccountNumberCounter


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
class UserProfileAdmin(admin.ModelAdmin):
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
class ProjectAdmin(admin.ModelAdmin):
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
