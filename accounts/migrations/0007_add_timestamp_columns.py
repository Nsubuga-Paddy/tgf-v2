# Migration to add missing timestamp columns to existing tables

from django.db import migrations


def get_table_columns(cursor, table_name):
    """Get list of existing columns in a table"""
    cursor.execute(f"PRAGMA table_info({table_name});")
    return [row[1] for row in cursor.fetchall()]


def add_timestamp_columns(apps, schema_editor):
    """Add missing timestamp columns (created_at, updated_at) to existing tables"""
    
    with schema_editor.connection.cursor() as cursor:
        # Check and add columns for WithdrawalRequest
        try:
            columns = get_table_columns(cursor, 'accounts_withdrawalrequest')
            if 'created_at' not in columns:
                cursor.execute("ALTER TABLE accounts_withdrawalrequest ADD COLUMN created_at DATETIME;")
            if 'updated_at' not in columns:
                cursor.execute("ALTER TABLE accounts_withdrawalrequest ADD COLUMN updated_at DATETIME;")
        except Exception as e:
            # Table might not exist, that's okay
            pass
        
        # Check and add columns for GWCContribution
        try:
            columns = get_table_columns(cursor, 'accounts_gwccontribution')
            if 'created_at' not in columns:
                cursor.execute("ALTER TABLE accounts_gwccontribution ADD COLUMN created_at DATETIME;")
            if 'updated_at' not in columns:
                cursor.execute("ALTER TABLE accounts_gwccontribution ADD COLUMN updated_at DATETIME;")
        except Exception as e:
            pass
        
        # Check and add columns for MESUInterest
        try:
            columns = get_table_columns(cursor, 'accounts_mesuinterest')
            if 'created_at' not in columns:
                cursor.execute("ALTER TABLE accounts_mesuinterest ADD COLUMN created_at DATETIME;")
            if 'updated_at' not in columns:
                cursor.execute("ALTER TABLE accounts_mesuinterest ADD COLUMN updated_at DATETIME;")
        except Exception as e:
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

