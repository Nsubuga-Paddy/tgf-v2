# Migration to add missing timestamp columns to existing tables

from django.db import migrations


def get_table_columns(cursor, table_name, db_vendor):
    """Get list of existing columns in a table - database agnostic"""
    if db_vendor == 'postgresql':
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = %s;
        """, [table_name])
        return [row[0] for row in cursor.fetchall()]
    elif db_vendor == 'sqlite':
        cursor.execute(f"PRAGMA table_info({table_name});")
        return [row[1] for row in cursor.fetchall()]
    else:
        # For other databases, return empty list and let try/except handle it
        return []


def add_timestamp_columns(apps, schema_editor):
    """Add missing timestamp columns (created_at, updated_at) to existing tables"""
    db_vendor = schema_editor.connection.vendor
    
    with schema_editor.connection.cursor() as cursor:
        # Check and add columns for WithdrawalRequest
        try:
            if db_vendor == 'postgresql':
                cursor.execute("ALTER TABLE accounts_withdrawalrequest ADD COLUMN IF NOT EXISTS created_at TIMESTAMP;")
                cursor.execute("ALTER TABLE accounts_withdrawalrequest ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;")
            else:
                columns = get_table_columns(cursor, 'accounts_withdrawalrequest', db_vendor)
                if 'created_at' not in columns:
                    cursor.execute("ALTER TABLE accounts_withdrawalrequest ADD COLUMN created_at DATETIME;")
                if 'updated_at' not in columns:
                    cursor.execute("ALTER TABLE accounts_withdrawalrequest ADD COLUMN updated_at DATETIME;")
        except Exception:
            pass
        
        # Check and add columns for GWCContribution
        try:
            if db_vendor == 'postgresql':
                cursor.execute("ALTER TABLE accounts_gwccontribution ADD COLUMN IF NOT EXISTS created_at TIMESTAMP;")
                cursor.execute("ALTER TABLE accounts_gwccontribution ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;")
            else:
                columns = get_table_columns(cursor, 'accounts_gwccontribution', db_vendor)
                if 'created_at' not in columns:
                    cursor.execute("ALTER TABLE accounts_gwccontribution ADD COLUMN created_at DATETIME;")
                if 'updated_at' not in columns:
                    cursor.execute("ALTER TABLE accounts_gwccontribution ADD COLUMN updated_at DATETIME;")
        except Exception:
            pass
        
        # Check and add columns for MESUInterest
        try:
            if db_vendor == 'postgresql':
                cursor.execute("ALTER TABLE accounts_mesuinterest ADD COLUMN IF NOT EXISTS created_at TIMESTAMP;")
                cursor.execute("ALTER TABLE accounts_mesuinterest ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;")
            else:
                columns = get_table_columns(cursor, 'accounts_mesuinterest', db_vendor)
                if 'created_at' not in columns:
                    cursor.execute("ALTER TABLE accounts_mesuinterest ADD COLUMN created_at DATETIME;")
                if 'updated_at' not in columns:
                    cursor.execute("ALTER TABLE accounts_mesuinterest ADD COLUMN updated_at DATETIME;")
        except Exception:
            pass


def reverse_add_timestamp_columns(apps, schema_editor):
    """Reverse migration - no-op since SQLite doesn't support DROP COLUMN easily"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_add_missing_columns_to_existing_tables'),
    ]

    operations = [
        migrations.RunPython(add_timestamp_columns, reverse_add_timestamp_columns),
    ]

