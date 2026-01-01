# Migration to add missing columns to existing tables
# This handles the case where tables were created manually or partially

from django.db import migrations


def add_missing_columns(apps, schema_editor):
    """Add missing columns to existing tables if they don't exist"""
    db_vendor = schema_editor.connection.vendor
    
    with schema_editor.connection.cursor() as cursor:
        # PostgreSQL uses IF NOT EXISTS, SQLite doesn't
        if db_vendor == 'postgresql':
            # PostgreSQL syntax
            for table, column, col_type in [
                ('accounts_withdrawalrequest', 'reason', 'TEXT'),
                ('accounts_withdrawalrequest', 'admin_notes', 'TEXT'),
                ('accounts_withdrawalrequest', 'processed_at', 'TIMESTAMP'),
                ('accounts_gwccontribution', 'admin_notes', 'TEXT'),
                ('accounts_gwccontribution', 'processed_at', 'TIMESTAMP'),
                ('accounts_mesuinterest', 'notes', 'TEXT'),
                ('accounts_mesuinterest', 'admin_notes', 'TEXT'),
                ('accounts_mesuinterest', 'processed_at', 'TIMESTAMP'),
            ]:
                try:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {col_type};")
                except Exception:
                    pass
        else:
            # SQLite or other databases - use try/except
            for table, column, col_type in [
                ('accounts_withdrawalrequest', 'reason', 'TEXT'),
                ('accounts_withdrawalrequest', 'admin_notes', 'TEXT'),
                ('accounts_withdrawalrequest', 'processed_at', 'DATETIME'),
                ('accounts_gwccontribution', 'admin_notes', 'TEXT'),
                ('accounts_gwccontribution', 'processed_at', 'DATETIME'),
                ('accounts_mesuinterest', 'notes', 'TEXT'),
                ('accounts_mesuinterest', 'admin_notes', 'TEXT'),
                ('accounts_mesuinterest', 'processed_at', 'DATETIME'),
            ]:
                try:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type};")
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

