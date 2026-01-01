from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import GWCGroup, GWCGroupMember, GWCContribution
from core.admin_base import ExportableAdminMixin


@admin.register(GWCGroup)
class GWCGroupAdmin(ExportableAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'created_by', 'total_contributed', 'target_amount', 'progress_bar', 'member_count', 'is_complete', 'is_active', 'created_at')
    list_filter = ('is_complete', 'is_active', 'created_at')
    search_fields = ('name', 'description', 'created_by__user__username', 'created_by__user__first_name', 'created_by__user__last_name')
    readonly_fields = ('total_contributed', 'progress_percentage', 'remaining_amount', 'member_count', 'created_at', 'updated_at', 'completed_at')
    
    fieldsets = (
        ('Group Information', {
            'fields': ('name', 'description', 'created_by')
        }),
        ('Financial Details', {
            'fields': ('target_amount', 'total_contributed', 'progress_percentage', 'remaining_amount')
        }),
        ('Status', {
            'fields': ('is_active', 'is_complete', 'member_count')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',)
        })
    )
    
    def progress_bar(self, obj):
        """Display progress as a visual bar"""
        percentage = obj.progress_percentage
        color = 'green' if percentage >= 100 else 'orange' if percentage >= 50 else 'red'
        return format_html(
            '<div style="width: 100px; background: #f0f0f0; border-radius: 4px; overflow: hidden;">'
            '<div style="width: {}%; background: {}; height: 20px; text-align: center; line-height: 20px; color: white; font-size: 11px;">{}%</div>'
            '</div>',
            percentage, color, int(percentage)
        )
    progress_bar.short_description = 'Progress'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by', 'created_by__user').prefetch_related('members')


@admin.register(GWCGroupMember)
class GWCGroupMemberAdmin(ExportableAdminMixin, admin.ModelAdmin):
    list_display = ('user_profile', 'group', 'contribution_amount', 'is_leader', 'joined_at')
    list_filter = ('is_leader', 'joined_at', 'group')
    search_fields = ('user_profile__user__username', 'user_profile__user__first_name', 'user_profile__user__last_name', 'group__name')
    readonly_fields = ('joined_at',)
    
    fieldsets = (
        ('Membership Information', {
            'fields': ('user_profile', 'group', 'contribution_amount', 'is_leader')
        }),
        ('Timestamps', {
            'fields': ('joined_at',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user_profile', 'user_profile__user', 'group')


@admin.register(GWCContribution)
class GWCContributionAdmin(ExportableAdminMixin, admin.ModelAdmin):
    list_display = ('user_profile', 'group', 'amount', 'receipt_number', 'contributed_at')
    list_filter = ('contributed_at', 'group')
    search_fields = ('user_profile__user__username', 'group__name', 'receipt_number')
    readonly_fields = ('contributed_at',)
    
    fieldsets = (
        ('Contribution Information', {
            'fields': ('user_profile', 'group', 'amount', 'receipt_number')
        }),
        ('Timestamps', {
            'fields': ('contributed_at',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user_profile', 'user_profile__user', 'group')
