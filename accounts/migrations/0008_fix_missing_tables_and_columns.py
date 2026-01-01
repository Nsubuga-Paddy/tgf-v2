# Migration to fix missing tables and columns
# Creates missing tables and adds missing columns to existing tables

from django.db import migrations, models
import django.db.models.deletion


def get_table_columns(cursor, table_name):
    """Get list of existing columns in a table"""
    try:
        cursor.execute(f"PRAGMA table_info({table_name});")
        return [row[1] for row in cursor.fetchall()]
    except Exception:
        return []


def table_exists(cursor, table_name):
    """Check if a table exists"""
    try:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
        return cursor.fetchone() is not None
    except Exception:
        return False


def fix_tables_and_columns(apps, schema_editor):
    """Fix missing tables and add missing columns"""
    
    with schema_editor.connection.cursor() as cursor:
        # Fix MESUInterest table - add missing columns
        if table_exists(cursor, 'accounts_mesuinterest'):
            columns = get_table_columns(cursor, 'accounts_mesuinterest')
            
            if 'investment_amount' not in columns:
                cursor.execute("ALTER TABLE accounts_mesuinterest ADD COLUMN investment_amount DECIMAL(12,2);")
            if 'number_of_shares' not in columns:
                cursor.execute("ALTER TABLE accounts_mesuinterest ADD COLUMN number_of_shares INTEGER DEFAULT 0;")
            if 'status' not in columns:
                cursor.execute("ALTER TABLE accounts_mesuinterest ADD COLUMN status VARCHAR(20) DEFAULT 'pending';")
            if 'user_profile_id' not in columns:
                # This is a foreign key, we need to handle it carefully
                cursor.execute("ALTER TABLE accounts_mesuinterest ADD COLUMN user_profile_id INTEGER;")
        
        # Create GWCContribution table if it doesn't exist
        if not table_exists(cursor, 'accounts_gwccontribution'):
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
            cursor.execute("CREATE INDEX accounts_gwccontribution_user_profile_id ON accounts_gwccontribution(user_profile_id);")
        
        # Ensure WithdrawalRequest has all columns
        if table_exists(cursor, 'accounts_withdrawalrequest'):
            columns = get_table_columns(cursor, 'accounts_withdrawalrequest')
            
            if 'amount' not in columns:
                cursor.execute("ALTER TABLE accounts_withdrawalrequest ADD COLUMN amount DECIMAL(12,2);")
            if 'status' not in columns:
                cursor.execute("ALTER TABLE accounts_withdrawalrequest ADD COLUMN status VARCHAR(20) DEFAULT 'pending';")
            if 'user_profile_id' not in columns:
                cursor.execute("ALTER TABLE accounts_withdrawalrequest ADD COLUMN user_profile_id INTEGER;")
        
        # Ensure MESUInterest table exists (create if it doesn't)
        if not table_exists(cursor, 'accounts_mesuinterest'):
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

