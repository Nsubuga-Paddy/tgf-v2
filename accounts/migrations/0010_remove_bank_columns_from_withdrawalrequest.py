# Migration to remove incorrect bank columns from WithdrawalRequest table
# Bank details should come from UserProfile, not be stored in WithdrawalRequest

from django.db import migrations


def column_exists(cursor, table_name, column_name, db_vendor):
    """Check if a column exists in a table - database agnostic with savepoint handling"""
    if db_vendor == 'postgresql':
        savepoint_id = f"check_col_{table_name}_{column_name}".replace('-', '_')
        try:
            cursor.execute(f"SAVEPOINT {savepoint_id};")
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = %s AND column_name = %s
                );
            """, [table_name, column_name])
            result = cursor.fetchone()[0]
            cursor.execute(f"RELEASE SAVEPOINT {savepoint_id};")
            return result
        except Exception:
            try:
                cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_id};")
            except Exception:
                pass
            return False
    elif db_vendor == 'sqlite':
        try:
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = [row[1] for row in cursor.fetchall()]
            return column_name in columns
        except Exception:
            return False
    else:
        return False


def table_exists(cursor, table_name, db_vendor):
    """Check if a table exists - database agnostic"""
    if db_vendor == 'postgresql':
        savepoint_id = f"check_table_{table_name}".replace('-', '_')
        try:
            cursor.execute(f"SAVEPOINT {savepoint_id};")
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                );
            """, [table_name])
            result = cursor.fetchone()[0]
            cursor.execute(f"RELEASE SAVEPOINT {savepoint_id};")
            return result
        except Exception:
            try:
                cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_id};")
            except Exception:
                pass
            return False
    elif db_vendor == 'sqlite':
        try:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
            return cursor.fetchone() is not None
        except Exception:
            return False
    else:
        return False


def remove_bank_columns(apps, schema_editor):
    """Remove incorrect bank columns from WithdrawalRequest table"""
    db_vendor = schema_editor.connection.vendor
    cursor = schema_editor.connection.cursor()
    
    try:
        table_name = 'accounts_withdrawalrequest'
        
        # Check if table exists
        if not table_exists(cursor, table_name, db_vendor):
            return  # Table doesn't exist, nothing to do
        
        # Columns that should be removed (bank details should come from UserProfile)
        columns_to_remove = ['bank_name', 'bank_account_number', 'bank_account_name']
        
        for column in columns_to_remove:
            if column_exists(cursor, table_name, column, db_vendor):
                if db_vendor == 'postgresql':
                    # PostgreSQL supports DROP COLUMN IF EXISTS
                    savepoint_id = f"drop_col_{column}".replace('-', '_')
                    try:
                        cursor.execute(f"SAVEPOINT {savepoint_id};")
                        cursor.execute(f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS {column};")
                        cursor.execute(f"RELEASE SAVEPOINT {savepoint_id};")
                    except Exception:
                        try:
                            cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_id};")
                        except Exception:
                            pass
                else:
                    # SQLite doesn't support DROP COLUMN easily, skip for now
                    # In production, this would need a table recreation
                    pass
                    
    finally:
        cursor.close()


def reverse_remove_bank_columns(apps, schema_editor):
    """Reverse migration - no-op since we don't want these columns back"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_fix_all_missing_tables_and_columns'),
    ]

    operations = [
        migrations.RunPython(remove_bank_columns, reverse_remove_bank_columns),
    ]

