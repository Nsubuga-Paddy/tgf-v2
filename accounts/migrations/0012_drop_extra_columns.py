# Migration to drop all extra columns not defined in models
# Ensures database schema matches model definitions exactly

from django.db import migrations


def get_all_columns(cursor, table_name, db_vendor):
    """Get all column names from a table"""
    if db_vendor == 'postgresql':
        savepoint_id = f"get_cols_{table_name}".replace('-', '_')
        try:
            cursor.execute(f"SAVEPOINT {savepoint_id};")
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position;
            """, [table_name])
            columns = [row[0] for row in cursor.fetchall()]
            cursor.execute(f"RELEASE SAVEPOINT {savepoint_id};")
            return columns
        except Exception:
            try:
                cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_id};")
            except Exception:
                pass
            return []
    elif db_vendor == 'sqlite':
        try:
            cursor.execute(f"PRAGMA table_info({table_name});")
            return [row[1] for row in cursor.fetchall()]
        except Exception:
            return []
    else:
        return []


def table_exists(cursor, table_name, db_vendor):
    """Check if a table exists"""
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


def drop_extra_columns(apps, schema_editor):
    """Drop all columns not defined in models"""
    db_vendor = schema_editor.connection.vendor
    cursor = schema_editor.connection.cursor()
    
    try:
        # Define the correct columns for each table based on models
        correct_columns = {
            'accounts_withdrawalrequest': [
                'id', 'user_profile_id', 'amount', 'reason', 
                'status', 'admin_notes', 'created_at', 'updated_at', 'processed_at'
            ],
            'accounts_gwccontribution': [
                'id', 'user_profile_id', 'amount', 'group_type',
                'status', 'admin_notes', 'created_at', 'updated_at', 'processed_at'
            ],
            'accounts_mesuinterest': [
                'id', 'user_profile_id', 'investment_amount', 'number_of_shares',
                'notes', 'status', 'admin_notes', 'created_at', 'updated_at', 'processed_at'
            ],
        }
        
        for table_name, expected_columns in correct_columns.items():
            if not table_exists(cursor, table_name, db_vendor):
                continue  # Skip if table doesn't exist
            
            # Get all current columns
            current_columns = get_all_columns(cursor, table_name, db_vendor)
            
            # Find columns that need to be dropped
            columns_to_drop = [col for col in current_columns if col not in expected_columns]
            
            # Drop each extra column
            for column in columns_to_drop:
                if db_vendor == 'postgresql':
                    savepoint_id = f"drop_{table_name}_{column}".replace('-', '_')
                    try:
                        cursor.execute(f"SAVEPOINT {savepoint_id};")
                        cursor.execute(f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS {column};")
                        cursor.execute(f"RELEASE SAVEPOINT {savepoint_id};")
                    except Exception:
                        # If it fails, rollback to savepoint and continue
                        try:
                            cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_id};")
                        except Exception:
                            pass
                else:
                    # SQLite doesn't support DROP COLUMN easily
                    # Would need table recreation
                    pass
                    
    finally:
        cursor.close()


def reverse_drop_extra_columns(apps, schema_editor):
    """Reverse migration - no-op since we don't want to re-add incorrect columns"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_fix_nullable_columns'),
    ]

    operations = [
        migrations.RunPython(drop_extra_columns, reverse_drop_extra_columns),
    ]

