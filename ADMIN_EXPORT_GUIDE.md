# Admin Export Functionality - User Guide

## Overview

Your MCS Financial Services admin site now includes powerful data export capabilities. Admin users can download data in three formats:
- **CSV** - Compatible with Excel, Google Sheets
- **Excel (.xlsx)** - Native Excel format with formatting
- **PDF** - Professional formatted reports

## How to Use

### Step 1: Navigate to Any Admin List Page

Go to any model's list page in the admin interface, for example:
- `/admin/savings_52_weeks/savingstransaction/`
- `/admin/savings_52_weeks/investment/`
- `/admin/accounts/userprofile/`
- `/admin/goat_farming/packagepurchase/`

### Step 2: Select Items to Export

1. Check the boxes next to the items you want to export
2. Or use "Select all X items" to export everything

### Step 3: Choose Export Format

From the **Action** dropdown menu at the top of the list, select one of:
- **Export selected [model] as CSV** - Quick and lightweight
- **Export selected [model] as Excel** - Best for Excel users
- **Export selected [model] as PDF** - Best for printing/sharing

### Step 4: Click "Go"

Your browser will automatically download the file with a timestamped filename.

## Export Features

### CSV Exports
- **Encoding**: UTF-8 with BOM for Excel compatibility
- **Columns**: All fields shown in the admin list display
- **Formatting**: Clean text, HTML tags removed
- **Best for**: Large datasets, database imports

### Excel Exports
- **Format**: Modern .xlsx format
- **Styling**: 
  - Professional blue header row
  - Auto-adjusted column widths
  - Clean grid layout
- **Columns**: All fields from admin list display
- **Best for**: Analysis, charts, presentations

### PDF Exports
- **Format**: Professional landscape layout
- **Styling**: 
  - Branded headers
  - Clean table formatting
  - Metadata footer with timestamp
- **Limit**: First 100 records (for performance)
- **Best for**: Reports, printing, sharing

## Filename Format

All exports use this naming convention:
```
{model_name_plural}_{timestamp}.{extension}
```

Examples:
- `savings_transactions_20251204_143022.csv`
- `investments_20251204_143055.xlsx`
- `user_profiles_20251204_143142.pdf`

## Models with Export Functionality

### Savings & Investments
- ✅ Savings Transactions
- ✅ Investments

### User Management
- ✅ User Profiles
- ✅ Projects

### Goat Farming
- ✅ Farms
- ✅ Management Fee Tiers
- ✅ Investment Packages
- ✅ Package Purchases
- ✅ User Farm Accounts
- ✅ Payments

## Tips & Best Practices

### 1. Use Filters First
Apply admin filters before exporting to get exactly the data you need:
```
Example: Filter by date range → Select all → Export
```

### 2. Choose the Right Format
- **Daily reports**: Use PDF for clean, shareable reports
- **Data analysis**: Use Excel for charts and calculations
- **Database work**: Use CSV for importing to other systems

### 3. Large Datasets
For very large exports (>1000 records):
- CSV exports handle unlimited records
- Excel exports handle unlimited records
- PDF exports are limited to 100 records (use CSV/Excel for more)

### 4. Column Customization
The exported columns match what you see in the admin list display. To customize:
1. Contact your developer to modify `list_display` in the admin configuration
2. Or use Django's column toggling if enabled

## Technical Details

### What Gets Exported
- All fields shown in `list_display`
- Calculated fields and custom admin methods
- Foreign key relationships (as string values)
- HTML fields are cleaned (tags removed)

### What Doesn't Get Exported
- Admin action checkboxes
- Edit/Delete links
- Raw HTML/formatting
- Related object lists (use separate exports)

## Troubleshooting

### Export Button Not Appearing?
- Ensure you have admin permissions
- Check that the page shows "Actions" dropdown
- Try refreshing the page

### File Won't Download?
- Check browser download settings
- Disable popup blockers for the admin site
- Try a different export format

### Missing Data in Export?
- Verify items are selected (checkboxes)
- Check that filters aren't hiding data
- Ensure you have permission to view the data

### PDF Only Shows 100 Records?
- This is by design for performance
- Use CSV or Excel for complete exports
- Or export in batches using filters

## Security & Privacy

### Who Can Export?
- Only authenticated admin users
- Respects Django's built-in admin permissions
- Same data you can view, you can export

### Data Protection
- Exports contain sensitive financial data
- Download files are not stored on the server
- Always use secure connections (HTTPS)
- Follow your organization's data handling policies

## Advanced Usage

### Customizing Exports (For Developers)

To customize which fields get exported:

```python
# In your admin.py file
class MyModelAdmin(ExportableAdminMixin, admin.ModelAdmin):
    list_display = ['field1', 'field2', 'field3']  # These will be exported
    
    # Optional: Override export methods for custom behavior
    def export_as_csv(self, request, queryset):
        from core.admin_exports import export_to_csv
        return export_to_csv(
            self, 
            request, 
            queryset,
            fields=['field1', 'field2'],  # Custom field selection
            filename='custom_name.csv'
        )
```

### Adding Export to New Models

When creating new admin classes:

```python
from django.contrib import admin
from core.admin_base import ExportableAdminMixin
from .models import MyModel

@admin.register(MyModel)
class MyModelAdmin(ExportableAdminMixin, admin.ModelAdmin):
    list_display = ['id', 'name', 'created_at']
    # Export actions are automatically added!
```

## Support

For technical issues or feature requests:
1. Check this guide first
2. Contact your system administrator
3. Refer to Django admin documentation

---

**Version**: 1.0  
**Last Updated**: December 4, 2025  
**System**: MCS Financial Services Administration

