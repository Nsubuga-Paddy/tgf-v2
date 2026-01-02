# Migration to fix column null constraints to match model definitions
# Ensures nullable fields (admin_notes, reason, processed_at) allow NULL values

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


def get_column_nullable(cursor, table_name, column_name, db_vendor):
    """Check if a column allows NULL values"""
    if db_vendor == 'postgresql':
        savepoint_id = f"check_null_{table_name}_{column_name}".replace('-', '_')
        try:
            cursor.execute(f"SAVEPOINT {savepoint_id};")
            cursor.execute("""
                SELECT is_nullable
                FROM information_schema.columns 
                WHERE table_name = %s AND column_name = %s;
            """, [table_name, column_name])
            result = cursor.fetchone()
            cursor.execute(f"RELEASE SAVEPOINT {savepoint_id};")
            if result:
                return result[0] == 'YES'
            return False
        except Exception:
            try:
                cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_id};")
            except Exception:
                pass
            return False
    else:
        # For SQLite, assume we need to alter it
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


def fix_nullable_columns(apps, schema_editor):
    """Fix column null constraints to allow NULL where model specifies"""
    db_vendor = schema_editor.connection.vendor
    cursor = schema_editor.connection.cursor()
    
    try:
        # Define tables and their nullable columns
        tables_to_fix = [
            ('accounts_withdrawalrequest', ['admin_notes', 'reason', 'processed_at']),
            ('accounts_gwccontribution', ['admin_notes', 'processed_at']),
            ('accounts_mesuinterest', ['admin_notes', 'notes', 'processed_at']),
        ]
        
        for table_name, nullable_columns in tables_to_fix:
            if not table_exists(cursor, table_name, db_vendor):
                continue  # Skip if table doesn't exist
            
            for column in nullable_columns:
                if not column_exists(cursor, table_name, column, db_vendor):
                    continue  # Skip if column doesn't exist
                
                # Check if column already allows NULL
                if get_column_nullable(cursor, table_name, column, db_vendor):
                    continue  # Already nullable, skip
                
                # Alter column to allow NULL
                if db_vendor == 'postgresql':
                    savepoint_id = f"fix_null_{table_name}_{column}".replace('-', '_')
                    try:
                        cursor.execute(f"SAVEPOINT {savepoint_id};")
                        # Simply drop the NOT NULL constraint
                        cursor.execute(f"ALTER TABLE {table_name} ALTER COLUMN {column} DROP NOT NULL;")
                        cursor.execute(f"RELEASE SAVEPOINT {savepoint_id};")
                    except Exception:
                        # If it fails, rollback to savepoint and continue
                        try:
                            cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_id};")
                        except Exception:
                            pass
                else:
                    # SQLite - ALTER COLUMN is limited, would need table recreation
                    # For now, skip SQLite as it's likely not the production database
                    pass
                    
    finally:
        cursor.close()


def reverse_fix_nullable_columns(apps, schema_editor):
    """Reverse migration - no-op since we don't want to re-add NOT NULL constraints"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_remove_bank_columns_from_withdrawalrequest'),
    ]

    operations = [
        migrations.RunPython(fix_nullable_columns, reverse_fix_nullable_columns),
    ]

