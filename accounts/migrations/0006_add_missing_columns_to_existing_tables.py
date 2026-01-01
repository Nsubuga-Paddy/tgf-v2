# Migration to add missing columns to existing tables
# This handles the case where tables were created manually or partially

from django.db import migrations, transaction


def table_exists(cursor, table_name, db_vendor):
    """Check if a table exists - database agnostic"""
    if db_vendor == 'postgresql':
        # Use savepoint to handle errors gracefully
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


def column_exists(cursor, table_name, column_name, db_vendor):
    """Check if a column exists in a table - database agnostic"""
    if db_vendor == 'postgresql':
        # Use savepoint to handle errors gracefully
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


def add_missing_columns(apps, schema_editor):
    """Add missing columns to existing tables if they don't exist"""
    db_vendor = schema_editor.connection.vendor
    
    # Define columns to add for each table
    columns_to_add = [
        ('accounts_withdrawalrequest', 'reason', 'TEXT'),
        ('accounts_withdrawalrequest', 'admin_notes', 'TEXT'),
        ('accounts_withdrawalrequest', 'processed_at', 'TIMESTAMP' if db_vendor == 'postgresql' else 'DATETIME'),
        ('accounts_gwccontribution', 'admin_notes', 'TEXT'),
        ('accounts_gwccontribution', 'processed_at', 'TIMESTAMP' if db_vendor == 'postgresql' else 'DATETIME'),
        ('accounts_mesuinterest', 'notes', 'TEXT'),
        ('accounts_mesuinterest', 'admin_notes', 'TEXT'),
        ('accounts_mesuinterest', 'processed_at', 'TIMESTAMP' if db_vendor == 'postgresql' else 'DATETIME'),
    ]
    
    cursor = schema_editor.connection.cursor()
    
    try:
        for table, column, col_type in columns_to_add:
            # Check if table exists first
            if not table_exists(cursor, table, db_vendor):
                continue  # Skip if table doesn't exist
            
            # Check if column already exists
            if column_exists(cursor, table, column, db_vendor):
                continue  # Skip if column already exists
            
            # Add the column using savepoint for PostgreSQL to handle errors gracefully
            if db_vendor == 'postgresql':
                # Use savepoint to handle errors without aborting the whole transaction
                savepoint_id = f"sp_{table}_{column}".replace('-', '_')
                try:
                    cursor.execute(f"SAVEPOINT {savepoint_id};")
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {col_type};")
                    cursor.execute(f"RELEASE SAVEPOINT {savepoint_id};")
                except Exception:
                    # Rollback to savepoint and continue
                    try:
                        cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_id};")
                    except Exception:
                        pass
                    continue
            else:
                # For SQLite, just try to add the column
                try:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type};")
                except Exception:
                    continue
    finally:
        cursor.close()


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

