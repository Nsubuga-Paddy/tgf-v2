# Migration to fix all missing tables and columns with proper error handling
# This ensures all required tables and columns exist

from django.db import migrations


def table_exists(cursor, table_name, db_vendor):
    """Check if a table exists - database agnostic with savepoint handling"""
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


def fix_all_tables_and_columns(apps, schema_editor):
    """Fix all missing tables and columns with proper error handling"""
    db_vendor = schema_editor.connection.vendor
    cursor = schema_editor.connection.cursor()
    
    try:
        # 1. Create accounts_gwccontribution table if it doesn't exist
        if not table_exists(cursor, 'accounts_gwccontribution', db_vendor):
            if db_vendor == 'postgresql':
                savepoint_id = "create_gwc_table"
                try:
                    cursor.execute(f"SAVEPOINT {savepoint_id};")
                    cursor.execute("""
                        CREATE TABLE accounts_gwccontribution (
                            id SERIAL PRIMARY KEY,
                            amount NUMERIC(12,2) NOT NULL,
                            group_type VARCHAR(20) NOT NULL,
                            status VARCHAR(20) NOT NULL DEFAULT 'pending',
                            admin_notes TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            processed_at TIMESTAMP,
                            user_profile_id INTEGER NOT NULL,
                            FOREIGN KEY (user_profile_id) REFERENCES accounts_userprofile(id)
                        );
                    """)
                    cursor.execute("CREATE INDEX accounts_gwccontribution_user_profile_id ON accounts_gwccontribution(user_profile_id);")
                    cursor.execute(f"RELEASE SAVEPOINT {savepoint_id};")
                except Exception:
                    try:
                        cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_id};")
                    except Exception:
                        pass
            else:
                try:
                    cursor.execute("""
                        CREATE TABLE accounts_gwccontribution (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            amount DECIMAL(12,2) NOT NULL,
                            group_type VARCHAR(20) NOT NULL,
                            status VARCHAR(20) NOT NULL DEFAULT 'pending',
                            admin_notes TEXT,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            processed_at DATETIME,
                            user_profile_id INTEGER NOT NULL,
                            FOREIGN KEY (user_profile_id) REFERENCES accounts_userprofile(id)
                        );
                    """)
                    cursor.execute("CREATE INDEX accounts_gwccontribution_user_profile_id ON accounts_gwccontribution(user_profile_id);")
                except Exception:
                    pass
        
        # 2. Fix accounts_withdrawalrequest - add missing columns
        if table_exists(cursor, 'accounts_withdrawalrequest', db_vendor):
            columns_to_add = [
                ('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP' if db_vendor == 'postgresql' else 'DATETIME DEFAULT CURRENT_TIMESTAMP'),
                ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP' if db_vendor == 'postgresql' else 'DATETIME DEFAULT CURRENT_TIMESTAMP'),
            ]
            
            for column, col_type in columns_to_add:
                if not column_exists(cursor, 'accounts_withdrawalrequest', column, db_vendor):
                    if db_vendor == 'postgresql':
                        savepoint_id = f"add_wr_{column}".replace('-', '_')
                        try:
                            cursor.execute(f"SAVEPOINT {savepoint_id};")
                            cursor.execute(f"ALTER TABLE accounts_withdrawalrequest ADD COLUMN {column} {col_type};")
                            cursor.execute(f"RELEASE SAVEPOINT {savepoint_id};")
                        except Exception:
                            try:
                                cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_id};")
                            except Exception:
                                pass
                    else:
                        try:
                            cursor.execute(f"ALTER TABLE accounts_withdrawalrequest ADD COLUMN {column} {col_type};")
                        except Exception:
                            pass
        
        # 3. Fix accounts_mesuinterest - add missing columns or create table
        if not table_exists(cursor, 'accounts_mesuinterest', db_vendor):
            # Create the entire table
            if db_vendor == 'postgresql':
                savepoint_id = "create_mesu_table"
                try:
                    cursor.execute(f"SAVEPOINT {savepoint_id};")
                    cursor.execute("""
                        CREATE TABLE accounts_mesuinterest (
                            id SERIAL PRIMARY KEY,
                            investment_amount NUMERIC(12,2) NOT NULL,
                            number_of_shares INTEGER NOT NULL DEFAULT 0,
                            notes TEXT,
                            status VARCHAR(20) NOT NULL DEFAULT 'pending',
                            admin_notes TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            processed_at TIMESTAMP,
                            user_profile_id INTEGER NOT NULL,
                            FOREIGN KEY (user_profile_id) REFERENCES accounts_userprofile(id)
                        );
                    """)
                    cursor.execute("CREATE INDEX accounts_mesuinterest_user_profile_id ON accounts_mesuinterest(user_profile_id);")
                    cursor.execute(f"RELEASE SAVEPOINT {savepoint_id};")
                except Exception:
                    try:
                        cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_id};")
                    except Exception:
                        pass
            else:
                try:
                    cursor.execute("""
                        CREATE TABLE accounts_mesuinterest (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            investment_amount DECIMAL(12,2) NOT NULL,
                            number_of_shares INTEGER NOT NULL DEFAULT 0,
                            notes TEXT,
                            status VARCHAR(20) NOT NULL DEFAULT 'pending',
                            admin_notes TEXT,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            processed_at DATETIME,
                            user_profile_id INTEGER NOT NULL,
                            FOREIGN KEY (user_profile_id) REFERENCES accounts_userprofile(id)
                        );
                    """)
                    cursor.execute("CREATE INDEX accounts_mesuinterest_user_profile_id ON accounts_mesuinterest(user_profile_id);")
                except Exception:
                    pass
        else:
            # Table exists, add missing columns
            columns_to_add = [
                ('investment_amount', 'NUMERIC(12,2)' if db_vendor == 'postgresql' else 'DECIMAL(12,2)'),
                ('number_of_shares', 'INTEGER DEFAULT 0'),
                ('notes', 'TEXT'),
                ('status', "VARCHAR(20) DEFAULT 'pending'"),
                ('admin_notes', 'TEXT'),
                ('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP' if db_vendor == 'postgresql' else 'DATETIME DEFAULT CURRENT_TIMESTAMP'),
                ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP' if db_vendor == 'postgresql' else 'DATETIME DEFAULT CURRENT_TIMESTAMP'),
                ('processed_at', 'TIMESTAMP' if db_vendor == 'postgresql' else 'DATETIME'),
                ('user_profile_id', 'INTEGER'),
            ]
            
            for column, col_type in columns_to_add:
                if not column_exists(cursor, 'accounts_mesuinterest', column, db_vendor):
                    if db_vendor == 'postgresql':
                        savepoint_id = f"add_mesu_{column}".replace('-', '_')
                        try:
                            cursor.execute(f"SAVEPOINT {savepoint_id};")
                            cursor.execute(f"ALTER TABLE accounts_mesuinterest ADD COLUMN {column} {col_type};")
                            cursor.execute(f"RELEASE SAVEPOINT {savepoint_id};")
                        except Exception:
                            try:
                                cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_id};")
                            except Exception:
                                pass
                    else:
                        try:
                            cursor.execute(f"ALTER TABLE accounts_mesuinterest ADD COLUMN {column} {col_type};")
                        except Exception:
                            pass
        
        # 4. Ensure accounts_gwccontribution has all columns if table exists
        if table_exists(cursor, 'accounts_gwccontribution', db_vendor):
            columns_to_add = [
                ('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP' if db_vendor == 'postgresql' else 'DATETIME DEFAULT CURRENT_TIMESTAMP'),
                ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP' if db_vendor == 'postgresql' else 'DATETIME DEFAULT CURRENT_TIMESTAMP'),
            ]
            
            for column, col_type in columns_to_add:
                if not column_exists(cursor, 'accounts_gwccontribution', column, db_vendor):
                    if db_vendor == 'postgresql':
                        savepoint_id = f"add_gwc_{column}".replace('-', '_')
                        try:
                            cursor.execute(f"SAVEPOINT {savepoint_id};")
                            cursor.execute(f"ALTER TABLE accounts_gwccontribution ADD COLUMN {column} {col_type};")
                            cursor.execute(f"RELEASE SAVEPOINT {savepoint_id};")
                        except Exception:
                            try:
                                cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_id};")
                            except Exception:
                                pass
                    else:
                        try:
                            cursor.execute(f"ALTER TABLE accounts_gwccontribution ADD COLUMN {column} {col_type};")
                        except Exception:
                            pass
                            
    finally:
        cursor.close()


def reverse_fix_all_tables_and_columns(apps, schema_editor):
    """Reverse migration - no-op since we're fixing existing issues"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_fix_missing_tables_and_columns'),
    ]

    operations = [
        migrations.RunPython(fix_all_tables_and_columns, reverse_fix_all_tables_and_columns),
    ]

