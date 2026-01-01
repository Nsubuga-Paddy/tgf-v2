# Migration to fix missing tables and columns
# Creates missing tables and adds missing columns to existing tables

from django.db import migrations, models
import django.db.models.deletion


def get_table_columns(cursor, table_name, db_vendor):
    """Get list of existing columns in a table - database agnostic"""
    try:
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
            return []
    except Exception:
        return []


def table_exists(cursor, table_name, db_vendor):
    """Check if a table exists - database agnostic"""
    try:
        if db_vendor == 'postgresql':
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                );
            """, [table_name])
            return cursor.fetchone()[0]
        elif db_vendor == 'sqlite':
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
            return cursor.fetchone() is not None
        else:
            return False
    except Exception:
        return False


def fix_tables_and_columns(apps, schema_editor):
    """Fix missing tables and add missing columns"""
    db_vendor = schema_editor.connection.vendor
    
    with schema_editor.connection.cursor() as cursor:
        # Fix MESUInterest table - add missing columns
        if table_exists(cursor, 'accounts_mesuinterest', db_vendor):
            columns = get_table_columns(cursor, 'accounts_mesuinterest', db_vendor)
            
            if 'investment_amount' not in columns:
                if db_vendor == 'postgresql':
                    cursor.execute("ALTER TABLE accounts_mesuinterest ADD COLUMN IF NOT EXISTS investment_amount NUMERIC(12,2);")
                else:
                    cursor.execute("ALTER TABLE accounts_mesuinterest ADD COLUMN investment_amount DECIMAL(12,2);")
            
            if 'number_of_shares' not in columns:
                if db_vendor == 'postgresql':
                    cursor.execute("ALTER TABLE accounts_mesuinterest ADD COLUMN IF NOT EXISTS number_of_shares INTEGER DEFAULT 0;")
                else:
                    cursor.execute("ALTER TABLE accounts_mesuinterest ADD COLUMN number_of_shares INTEGER DEFAULT 0;")
            
            if 'status' not in columns:
                if db_vendor == 'postgresql':
                    cursor.execute("ALTER TABLE accounts_mesuinterest ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'pending';")
                else:
                    cursor.execute("ALTER TABLE accounts_mesuinterest ADD COLUMN status VARCHAR(20) DEFAULT 'pending';")
            
            if 'user_profile_id' not in columns:
                if db_vendor == 'postgresql':
                    cursor.execute("ALTER TABLE accounts_mesuinterest ADD COLUMN IF NOT EXISTS user_profile_id INTEGER;")
                else:
                    cursor.execute("ALTER TABLE accounts_mesuinterest ADD COLUMN user_profile_id INTEGER;")
        
        # Create GWCContribution table if it doesn't exist
        if not table_exists(cursor, 'accounts_gwccontribution', db_vendor):
            if db_vendor == 'postgresql':
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS accounts_gwccontribution (
                        id SERIAL PRIMARY KEY,
                        amount NUMERIC(12,2) NOT NULL,
                        group_type VARCHAR(20) NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'pending',
                        admin_notes TEXT,
                        created_at TIMESTAMP,
                        updated_at TIMESTAMP,
                        processed_at TIMESTAMP,
                        user_profile_id INTEGER NOT NULL,
                        FOREIGN KEY (user_profile_id) REFERENCES accounts_userprofile(id)
                    );
                """)
            else:
                cursor.execute("""
                    CREATE TABLE accounts_gwccontribution (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        amount DECIMAL(12,2) NOT NULL,
                        group_type VARCHAR(20) NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'pending',
                        admin_notes TEXT,
                        created_at DATETIME,
                        updated_at DATETIME,
                        processed_at DATETIME,
                        user_profile_id INTEGER NOT NULL,
                        FOREIGN KEY (user_profile_id) REFERENCES accounts_userprofile(id)
                    );
                """)
            # Create index on user_profile_id
            if db_vendor == 'postgresql':
                cursor.execute("CREATE INDEX IF NOT EXISTS accounts_gwccontribution_user_profile_id ON accounts_gwccontribution(user_profile_id);")
            else:
                cursor.execute("CREATE INDEX accounts_gwccontribution_user_profile_id ON accounts_gwccontribution(user_profile_id);")
        
        # Ensure WithdrawalRequest has all columns
        if table_exists(cursor, 'accounts_withdrawalrequest', db_vendor):
            columns = get_table_columns(cursor, 'accounts_withdrawalrequest', db_vendor)
            
            if 'amount' not in columns:
                if db_vendor == 'postgresql':
                    cursor.execute("ALTER TABLE accounts_withdrawalrequest ADD COLUMN IF NOT EXISTS amount NUMERIC(12,2);")
                else:
                    cursor.execute("ALTER TABLE accounts_withdrawalrequest ADD COLUMN amount DECIMAL(12,2);")
            
            if 'status' not in columns:
                if db_vendor == 'postgresql':
                    cursor.execute("ALTER TABLE accounts_withdrawalrequest ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'pending';")
                else:
                    cursor.execute("ALTER TABLE accounts_withdrawalrequest ADD COLUMN status VARCHAR(20) DEFAULT 'pending';")
            
            if 'user_profile_id' not in columns:
                if db_vendor == 'postgresql':
                    cursor.execute("ALTER TABLE accounts_withdrawalrequest ADD COLUMN IF NOT EXISTS user_profile_id INTEGER;")
                else:
                    cursor.execute("ALTER TABLE accounts_withdrawalrequest ADD COLUMN user_profile_id INTEGER;")
        
        # Ensure MESUInterest table exists (create if it doesn't)
        if not table_exists(cursor, 'accounts_mesuinterest', db_vendor):
            if db_vendor == 'postgresql':
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS accounts_mesuinterest (
                        id SERIAL PRIMARY KEY,
                        investment_amount NUMERIC(12,2) NOT NULL,
                        number_of_shares INTEGER NOT NULL DEFAULT 0,
                        notes TEXT,
                        status VARCHAR(20) NOT NULL DEFAULT 'pending',
                        admin_notes TEXT,
                        created_at TIMESTAMP,
                        updated_at TIMESTAMP,
                        processed_at TIMESTAMP,
                        user_profile_id INTEGER NOT NULL,
                        FOREIGN KEY (user_profile_id) REFERENCES accounts_userprofile(id)
                    );
                """)
            else:
                cursor.execute("""
                    CREATE TABLE accounts_mesuinterest (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        investment_amount DECIMAL(12,2) NOT NULL,
                        number_of_shares INTEGER NOT NULL DEFAULT 0,
                        notes TEXT,
                        status VARCHAR(20) NOT NULL DEFAULT 'pending',
                        admin_notes TEXT,
                        created_at DATETIME,
                        updated_at DATETIME,
                        processed_at DATETIME,
                        user_profile_id INTEGER NOT NULL,
                        FOREIGN KEY (user_profile_id) REFERENCES accounts_userprofile(id)
                    );
                """)
            if db_vendor == 'postgresql':
                cursor.execute("CREATE INDEX IF NOT EXISTS accounts_mesuinterest_user_profile_id ON accounts_mesuinterest(user_profile_id);")
            else:
                cursor.execute("CREATE INDEX accounts_mesuinterest_user_profile_id ON accounts_mesuinterest(user_profile_id);")


def reverse_fix_tables_and_columns(apps, schema_editor):
    """Reverse migration - no-op since we're fixing existing issues"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_add_timestamp_columns'),
    ]

    operations = [
        migrations.RunPython(fix_tables_and_columns, reverse_fix_tables_and_columns),
    ]

