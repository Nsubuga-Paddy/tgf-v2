# Data migration to create GeneralAccount records for all existing users

from django.db import migrations
from decimal import Decimal


def create_general_accounts(apps, schema_editor):
    """
    Create GeneralAccount records for all existing users who don't have one.
    This ensures every user has a general account.
    """
    UserProfile = apps.get_model('accounts', 'UserProfile')
    GeneralAccount = apps.get_model('accounts', 'GeneralAccount')
    
    created = 0
    for profile in UserProfile.objects.all():
        general_account, was_created = GeneralAccount.objects.get_or_create(
            user_profile=profile,
            defaults={'balance': Decimal('0.00')}
        )
        if was_created:
            created += 1
    
    print(f"✓ Created {created} general accounts for existing users")


def reverse_create_accounts(apps, schema_editor):
    """Reverse migration - delete all general accounts (optional, for rollback)"""
    GeneralAccount = apps.get_model('accounts', 'GeneralAccount')
    count = GeneralAccount.objects.count()
    GeneralAccount.objects.all().delete()
    print(f"✓ Deleted {count} general accounts")


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_add_general_account'),
    ]

    operations = [
        migrations.RunPython(create_general_accounts, reverse_create_accounts),
    ]

