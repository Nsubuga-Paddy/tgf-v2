"""
Base Admin Classes with Export Functionality
"""
from django.contrib import admin
from .admin_exports import create_export_actions


class ExportableAdminMixin:
    """
    Mixin to add CSV, Excel, and PDF export actions to any ModelAdmin.
    
    Usage:
        @admin.register(MyModel)
        class MyModelAdmin(ExportableAdminMixin, admin.ModelAdmin):
            # Your existing admin configuration
            pass
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add export actions dynamically
        model_name = self.model._meta.verbose_name_plural
        export_actions = create_export_actions(model_name)
        
        # Merge with existing actions
        if self.actions is None:
            self.actions = export_actions
        else:
            # Ensure actions is a list
            if not isinstance(self.actions, list):
                self.actions = list(self.actions)
            self.actions.extend(export_actions)


class ExportableModelAdmin(ExportableAdminMixin, admin.ModelAdmin):
    """
    Base ModelAdmin class with built-in CSV, Excel, and PDF export functionality.
    
    Usage:
        @admin.register(MyModel)
        class MyModelAdmin(ExportableModelAdmin):
            list_display = ['field1', 'field2', 'field3']
            # Your other admin configuration
    """
    pass

