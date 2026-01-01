# Migration to add missing columns to existing tables
# This handles the case where tables were created manually or partially

from django.db import migrations


def add_missing_columns(apps, schema_editor):
    """Add missing columns to existing tables if they don't exist"""
    db_alias = schema_editor.connection.alias
    
    # For SQLite, we need to check if columns exist before adding
    # SQLite doesn't support IF NOT EXISTS for ALTER TABLE ADD COLUMN
    # So we'll use a try-except approach
    
    with schema_editor.connection.cursor() as cursor:
        # Check and add columns for WithdrawalRequest
        try:
            cursor.execute("ALTER TABLE accounts_withdrawalrequest ADD COLUMN reason TEXT;")
        except Exception:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE accounts_withdrawalrequest ADD COLUMN admin_notes TEXT;")
        except Exception:
            pass
        
        try:
            cursor.execute("ALTER TABLE accounts_withdrawalrequest ADD COLUMN processed_at DATETIME;")
        except Exception:
            pass
        
        # Check and add columns for GWCContribution
        try:
            cursor.execute("ALTER TABLE accounts_gwccontribution ADD COLUMN admin_notes TEXT;")
        except Exception:
            pass
        
        try:
            cursor.execute("ALTER TABLE accounts_gwccontribution ADD COLUMN processed_at DATETIME;")
        except Exception:
            pass
        
        # Check and add columns for MESUInterest
        try:
            cursor.execute("ALTER TABLE accounts_mesuinterest ADD COLUMN notes TEXT;")
        except Exception:
            pass
        
        try:
            cursor.execute("ALTER TABLE accounts_mesuinterest ADD COLUMN admin_notes TEXT;")
        except Exception:
            pass
        
        try:
            cursor.execute("ALTER TABLE accounts_mesuinterest ADD COLUMN processed_at DATETIME;")
        except Exception:
            pass


def reverse_add_missing_columns(apps, schema_editor):
    """Reverse migration - no-op since SQLite doesn't support DROP COLUMN easily"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_make_whatsapp_number_required'),
    ]

    operations = [
        migrations.RunPython(add_missing_columns, reverse_add_missing_columns),
    ]

