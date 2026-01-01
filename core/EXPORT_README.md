# Admin Export Module - Developer Documentation

## Quick Start

### 1. Basic Usage (Recommended)

Use the `ExportableAdminMixin` to add export functionality to any admin class:

```python
from django.contrib import admin
from core.admin_base import ExportableAdminMixin
from .models import MyModel

@admin.register(MyModel)
class MyModelAdmin(ExportableAdminMixin, admin.ModelAdmin):
    list_display = ['id', 'name', 'created_at']
    # Export actions (CSV, Excel, PDF) are automatically added!
```

### 2. Alternative: Use Base Class

```python
from core.admin_base import ExportableModelAdmin

@admin.register(MyModel)
class MyModelAdmin(ExportableModelAdmin):
    list_display = ['id', 'name', 'created_at']
```

### 3. Manual Setup (Advanced)

```python
from django.contrib import admin
from core.admin_exports import create_export_actions

@admin.register(MyModel)
class MyModelAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'created_at']
    actions = create_export_actions('MyModel')
```

## Module Structure

```
core/
├── admin_base.py         # Base classes and mixins
├── admin_exports.py      # Export utility functions
└── EXPORT_README.md      # This file
```

## API Reference

### ExportableAdminMixin

**Purpose**: Mixin class that adds CSV, Excel, and PDF export actions to any ModelAdmin.

**Usage**:
```python
class MyAdmin(ExportableAdminMixin, admin.ModelAdmin):
    pass
```

**Features**:
- Automatically adds 3 export actions
- Works with existing admin actions
- Uses `list_display` fields for columns
- Handles custom admin methods

### ExportableModelAdmin

**Purpose**: Pre-configured ModelAdmin base class with export functionality.

**Usage**:
```python
class MyAdmin(ExportableModelAdmin):
    pass
```

**Inherits from**:
- `ExportableAdminMixin`
- `admin.ModelAdmin`

### export_to_csv()

**Signature**:
```python
def export_to_csv(
    modeladmin, 
    request, 
    queryset, 
    filename: str = None, 
    fields: List[str] = None
) -> HttpResponse
```

**Parameters**:
- `modeladmin`: ModelAdmin instance
- `request`: HttpRequest object
- `queryset`: QuerySet to export
- `filename`: Optional custom filename (auto-generated if None)
- `fields`: Optional list of field names (uses list_display if None)

**Returns**: HttpResponse with CSV content

**Example**:
```python
from core.admin_exports import export_to_csv

class MyAdmin(admin.ModelAdmin):
    def custom_csv_export(self, request, queryset):
        return export_to_csv(
            self, 
            request, 
            queryset,
            filename='custom_report.csv',
            fields=['id', 'name', 'email']
        )
    custom_csv_export.short_description = "Export as Custom CSV"
    
    actions = ['custom_csv_export']
```

### export_to_excel()

**Signature**:
```python
def export_to_excel(
    modeladmin, 
    request, 
    queryset, 
    filename: str = None, 
    fields: List[str] = None
) -> HttpResponse
```

**Parameters**: Same as `export_to_csv()`

**Returns**: HttpResponse with Excel (.xlsx) content

**Features**:
- Professional blue header styling
- Auto-adjusted column widths
- Grid borders
- Falls back to CSV if openpyxl not installed

**Example**:
```python
from core.admin_exports import export_to_excel

def custom_excel_export(self, request, queryset):
    return export_to_excel(
        self,
        request,
        queryset,
        filename='financial_report.xlsx',
        fields=['date', 'amount', 'user']
    )
```

### export_to_pdf()

**Signature**:
```python
def export_to_pdf(
    modeladmin, 
    request, 
    queryset, 
    filename: str = None, 
    fields: List[str] = None,
    title: str = None,
    orientation: str = 'landscape'
) -> HttpResponse
```

**Parameters**:
- `modeladmin`: ModelAdmin instance
- `request`: HttpRequest object
- `queryset`: QuerySet to export
- `filename`: Optional custom filename
- `fields`: Optional list of field names
- `title`: Optional report title (uses model verbose_name_plural if None)
- `orientation`: 'portrait' or 'landscape' (default: 'landscape')

**Returns**: HttpResponse with PDF content

**Limitations**:
- Limited to first 100 records for performance
- Long text values are truncated to 50 characters
- Falls back to CSV if reportlab not installed

**Example**:
```python
from core.admin_exports import export_to_pdf

def monthly_report(self, request, queryset):
    return export_to_pdf(
        self,
        request,
        queryset,
        title='Monthly Financial Report',
        orientation='portrait',
        fields=['date', 'description', 'amount']
    )
```

### create_export_actions()

**Signature**:
```python
def create_export_actions(model_name: str) -> List[Callable]
```

**Parameters**:
- `model_name`: Display name for the model (used in action descriptions)

**Returns**: List of 3 action functions [csv, excel, pdf]

**Example**:
```python
from core.admin_exports import create_export_actions

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    actions = create_export_actions('Transaction')
```

## Customization

### Custom Field Selection

```python
class MyAdmin(ExportableAdminMixin, admin.ModelAdmin):
    list_display = ['id', 'name', 'email', 'is_active']
    
    def export_active_only(self, request, queryset):
        from core.admin_exports import export_to_excel
        active_users = queryset.filter(is_active=True)
        return export_to_excel(
            self,
            request,
            active_users,
            fields=['name', 'email'],  # Only these fields
            filename='active_users.xlsx'
        )
    export_active_only.short_description = "Export active users"
    
    actions = ['export_active_only']
```

### Custom Styling (Excel)

To add custom Excel styling, modify `export_to_excel()` in `admin_exports.py`:

```python
# Example: Add conditional formatting
from openpyxl.styles import PatternFill

for row_num, obj in enumerate(queryset, 2):
    for col_num, field_name in enumerate(field_names, 1):
        cell = ws.cell(row=row_num, column=col_num, value=value)
        
        # Custom: Highlight negative amounts in red
        if field_name == 'amount' and value < 0:
            cell.fill = PatternFill(
                start_color="FFCCCC", 
                end_color="FFCCCC", 
                fill_type="solid"
            )
```

### Custom PDF Layout

Modify `export_to_pdf()` for custom layouts:

```python
# Add company logo
from reportlab.platypus import Image

logo = Image('path/to/logo.png', width=2*inch, height=1*inch)
elements.insert(0, logo)

# Add custom footer
footer = Paragraph(
    "© 2025 MCS Financial Services | Confidential",
    styles['Normal']
)
elements.append(footer)
```

## Best Practices

### 1. Field Selection

Always specify relevant fields for exports:
```python
# Good: Specific fields
fields=['id', 'name', 'amount', 'date']

# Avoid: Too many fields
fields=None  # Uses all list_display fields (might be too many)
```

### 2. Performance

For large datasets:
```python
# Use select_related and prefetch_related
def get_queryset(self, request):
    qs = super().get_queryset(request)
    return qs.select_related('user', 'profile')

# Limit querysets for PDF
def export_pdf(self, request, queryset):
    # PDFs already limited to 100 records
    return export_to_pdf(self, request, queryset)
```

### 3. Security

```python
# Add permission checks
def export_sensitive_data(self, request, queryset):
    if not request.user.has_perm('app.export_sensitive'):
        self.message_user(
            request, 
            "You don't have permission", 
            level='ERROR'
        )
        return
    return export_to_csv(self, request, queryset)
```

### 4. Error Handling

```python
def custom_export(self, request, queryset):
    try:
        return export_to_excel(self, request, queryset)
    except Exception as e:
        self.message_user(
            request, 
            f"Export failed: {str(e)}", 
            level='ERROR'
        )
```

## Dependencies

### Required
- `django>=3.2`

### Optional (for full functionality)
- `openpyxl>=3.0.0` - For Excel exports
- `reportlab>=3.6.0` - For PDF exports

### Installation

```bash
pip install openpyxl reportlab
```

Or add to `requirements.txt`:
```
openpyxl==3.1.2
reportlab==4.0.7
```

## Fallback Behavior

If optional dependencies are missing:
- `export_to_excel()` → Falls back to CSV
- `export_to_pdf()` → Falls back to CSV

Users still get their data, just in CSV format.

## Testing

```python
# Test export actions
from django.test import TestCase, RequestFactory
from django.contrib.admin.sites import AdminSite
from .admin import MyModelAdmin
from .models import MyModel

class ExportTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin = MyModelAdmin(MyModel, AdminSite())
    
    def test_csv_export(self):
        request = self.factory.get('/admin/app/mymodel/')
        queryset = MyModel.objects.all()
        response = self.admin.export_as_csv(request, queryset)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('attachment', response['Content-Disposition'])
```

## Troubleshooting

### Issue: Actions not showing

**Solution**:
```python
# Ensure actions are enabled in admin
class MyAdmin(ExportableAdminMixin, admin.ModelAdmin):
    # This should be None or a list, not False
    # actions = False  # Wrong!
    pass  # Correct (defaults to None)
```

### Issue: Wrong columns exported

**Solution**:
```python
# Specify fields explicitly
def export_action(self, request, queryset):
    return export_to_csv(
        self, 
        request, 
        queryset,
        fields=['field1', 'field2']  # Explicit
    )
```

### Issue: HTML in exports

**Solution**: HTML is automatically cleaned, but for complex HTML:
```python
# In your model or admin
def clean_field(self, obj):
    import re
    html = obj.description
    return re.sub('<[^<]+?>', '', html)
clean_field.short_description = 'Description'
```

## Migration Guide

### From Custom Export Code

**Before**:
```python
def export_csv(modeladmin, request, queryset):
    import csv
    response = HttpResponse(content_type='text/csv')
    writer = csv.writer(response)
    # ... custom code ...
    return response
```

**After**:
```python
from core.admin_exports import export_to_csv

def export_csv(modeladmin, request, queryset):
    return export_to_csv(modeladmin, request, queryset)
```

### Adding to Existing Admin Classes

**Before**:
```python
@admin.register(MyModel)
class MyModelAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
```

**After**:
```python
from core.admin_base import ExportableAdminMixin

@admin.register(MyModel)
class MyModelAdmin(ExportableAdminMixin, admin.ModelAdmin):
    list_display = ['id', 'name']
```

## License & Support

Part of MCS Financial Services Administration System

For issues or questions:
- Check Django admin documentation
- Review this guide
- Contact development team

