# Setup Guide - Admin Export Functionality

## Installation Steps

### Step 1: Install Dependencies

Run the following command in your project directory:

```bash
pip install -r requirements.txt
```

This will install:
- `openpyxl==3.1.2` - For Excel exports
- `reportlab==4.0.7` - For PDF exports

### Step 2: Verify Installation

Check if the packages are installed:

```bash
pip list | grep openpyxl
pip list | grep reportlab
```

You should see:
```
openpyxl    3.1.2
reportlab   4.0.7
```

### Step 3: Test the Functionality

1. **Start your development server**:
   ```bash
   python manage.py runserver
   ```

2. **Login to the admin site**:
   - Go to `http://127.0.0.1:8000/admin/`
   - Login with your admin credentials

3. **Navigate to any model** (e.g., Savings Transactions):
   - Go to `http://127.0.0.1:8000/admin/savings_52_weeks/savingstransaction/`

4. **Test the export**:
   - Select one or more items using the checkboxes
   - In the "Action" dropdown at the top, you should see:
     - "Export selected savings transactions as CSV"
     - "Export selected savings transactions as Excel"
     - "Export selected savings transactions as PDF"
   - Select one and click "Go"
   - Your browser should download the file

## What Was Changed

### New Files Created:

1. **`core/admin_exports.py`** - Export utility functions
   - `export_to_csv()` - CSV export function
   - `export_to_excel()` - Excel export function
   - `export_to_pdf()` - PDF export function
   - `create_export_actions()` - Factory function

2. **`core/admin_base.py`** - Base classes
   - `ExportableAdminMixin` - Mixin for adding exports
   - `ExportableModelAdmin` - Ready-to-use base class

3. **`ADMIN_EXPORT_GUIDE.md`** - User documentation
4. **`core/EXPORT_README.md`** - Developer documentation
5. **`SETUP_EXPORTS.md`** - This file

### Modified Files:

1. **`requirements.txt`**
   - Added: `openpyxl==3.1.2`
   - Added: `reportlab==4.0.7`

2. **`savings_52_weeks/admin.py`**
   - Added: `ExportableAdminMixin` to `SavingsTransactionAdmin`
   - Added: `ExportableAdminMixin` to `InvestmentAdmin`

3. **`accounts/admin.py`**
   - Added: `ExportableAdminMixin` to `UserProfileAdmin`
   - Added: `ExportableAdminMixin` to `ProjectAdmin`

4. **`goat_farming/admin.py`**
   - Added: `ExportableAdminMixin` to all admin classes:
     - `FarmAdmin`
     - `ManagementFeeTierAdmin`
     - `InvestmentPackageAdmin`
     - `PackagePurchaseAdmin`
     - `UserFarmAccountAdmin`
     - `PaymentAdmin`

## Models with Export Functionality

✅ **Savings & Investments**
- Savings Transactions (CSV, Excel, PDF)
- Investments (CSV, Excel, PDF)

✅ **User Management**
- User Profiles (CSV, Excel, PDF)
- Projects (CSV, Excel, PDF)

✅ **Goat Farming**
- Farms (CSV, Excel, PDF)
- Management Fee Tiers (CSV, Excel, PDF)
- Investment Packages (CSV, Excel, PDF)
- Package Purchases (CSV, Excel, PDF)
- User Farm Accounts (CSV, Excel, PDF)
- Payments (CSV, Excel, PDF)

## How It Works

### For Admin Users:
1. Login to admin site
2. Navigate to any model list page
3. Select items to export
4. Choose export format from Actions dropdown
5. Click "Go" to download

### For Developers:
The export functionality is added via a mixin pattern:

```python
from core.admin_base import ExportableAdminMixin

@admin.register(MyModel)
class MyModelAdmin(ExportableAdminMixin, admin.ModelAdmin):
    list_display = ['field1', 'field2']
    # Export actions automatically added!
```

## Adding to New Models

When you create new admin classes in the future:

```python
# In your app's admin.py
from django.contrib import admin
from core.admin_base import ExportableAdminMixin
from .models import NewModel

@admin.register(NewModel)
class NewModelAdmin(ExportableAdminMixin, admin.ModelAdmin):
    list_display = ['id', 'name', 'created_at']
    # Export functionality is now available!
```

## Troubleshooting

### Issue: "No module named 'openpyxl'"

**Solution**: Install the dependencies:
```bash
pip install openpyxl reportlab
```

### Issue: Export buttons not showing

**Possible causes**:
1. Browser cache - Try hard refresh (Ctrl+F5)
2. Server not restarted - Restart Django server
3. Not logged in as admin - Verify admin permissions

**Solution**:
```bash
# Stop the server (Ctrl+C)
# Restart it
python manage.py runserver
```

### Issue: Excel opens with garbled text

**Solution**: The files use UTF-8 encoding. This should work automatically in Excel 2016+. For older Excel:
1. Open Excel
2. Go to Data → Get External Data → From Text
3. Select UTF-8 encoding
4. Import the CSV file

### Issue: PDF only shows some records

**Expected behavior**: PDFs are limited to 100 records for performance. Use CSV or Excel for complete exports.

## Production Deployment

### Before Deploying:

1. **Verify dependencies in production environment**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Collect static files** (if needed):
   ```bash
   python manage.py collectstatic --noinput
   ```

3. **Test in staging** first

4. **Update deployment scripts** to include new dependencies

### Security Considerations:

- ✅ Only admin users can export (Django built-in permissions)
- ✅ Exports respect user permissions
- ✅ Files are not stored on server (direct download)
- ✅ HTTPS should be used in production
- ⚠️ Monitor export activity in logs
- ⚠️ Consider rate limiting for large exports

### Performance Tips:

1. **Use database indexes** on frequently exported fields
2. **Enable database query optimization**:
   ```python
   def get_queryset(self, request):
       qs = super().get_queryset(request)
       return qs.select_related('user', 'profile')
   ```
3. **Limit PDF exports** to reasonable sizes (already implemented: 100 records)
4. **Consider async exports** for very large datasets (future enhancement)

## Testing Checklist

Before going live, test:

- [ ] CSV export works
- [ ] Excel export works
- [ ] PDF export works
- [ ] Exported data is correct
- [ ] File downloads successfully
- [ ] Multiple selections work
- [ ] "Select all" works
- [ ] Filters work before export
- [ ] Custom admin methods export correctly
- [ ] Foreign keys display properly
- [ ] Date/time formats are correct
- [ ] Currency formats are preserved
- [ ] HTML is stripped from exports
- [ ] Unicode characters work (test with Ugandan names)

## Next Steps

1. **Review the user guide**: `ADMIN_EXPORT_GUIDE.md`
2. **Read developer docs**: `core/EXPORT_README.md`
3. **Test the functionality**: Follow Step 3 above
4. **Train your admin users**: Share the user guide
5. **Monitor usage**: Check logs for any issues

## Support

For issues or questions:
- Check this setup guide
- Review the documentation files
- Test in development environment first
- Check Django logs for errors

## Version History

- **v1.0** (2025-12-04): Initial implementation
  - CSV, Excel, PDF exports
  - Applied to savings_52_weeks, accounts, goat_farming apps
  - User and developer documentation

---

**System**: MCS Financial Services Administration  
**Status**: ✅ Ready for Testing  
**Documentation**: Complete

