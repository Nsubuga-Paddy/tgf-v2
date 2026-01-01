# Data migration to backfill challenge_year for existing SavingsTransaction records

from django.db import migrations
from django.db.models import F


def backfill_challenge_year(apps, schema_editor):
    """
    Backfill challenge_year for ALL existing SavingsTransaction records.
    Uses bulk_update for efficiency and handles all cases:
    - Transactions with transaction_date: use the year from transaction_date
    - Transactions without transaction_date: use year from date_saved
    - Transactions with neither: default to 2025
    """
    SavingsTransaction = apps.get_model('savings_52_weeks', 'SavingsTransaction')
    
    # Get ALL transactions that need challenge_year set (including those that might be None)
    transactions_to_update = []
    
    # Process transactions with transaction_date
    transactions_with_date = SavingsTransaction.objects.filter(
        challenge_year__isnull=True,
        transaction_date__isnull=False
    )
    for transaction in transactions_with_date:
        transaction.challenge_year = transaction.transaction_date.year
        transactions_to_update.append(transaction)
    
    # Process transactions without transaction_date but with date_saved
    transactions_without_date = SavingsTransaction.objects.filter(
        challenge_year__isnull=True,
        transaction_date__isnull=True,
        date_saved__isnull=False
    )
    for transaction in transactions_without_date:
        # Use year from date_saved
        transaction.challenge_year = transaction.date_saved.year if transaction.date_saved else 2025
        transactions_to_update.append(transaction)
    
    # Process any remaining transactions (default to 2025)
    remaining = SavingsTransaction.objects.filter(
        challenge_year__isnull=True
    )
    for transaction in remaining:
        transaction.challenge_year = 2025
        transactions_to_update.append(transaction)
    
    # Bulk update all transactions
    if transactions_to_update:
        SavingsTransaction.objects.bulk_update(transactions_to_update, ['challenge_year'], batch_size=1000)
        print(f"✓ Backfilled challenge_year for {len(transactions_to_update)} transactions")
    else:
        print("✓ No transactions needed challenge_year backfill")
    
    # Verify: Check if there are any remaining transactions without challenge_year
    remaining_count = SavingsTransaction.objects.filter(challenge_year__isnull=True).count()
    if remaining_count > 0:
        print(f"⚠ Warning: {remaining_count} transactions still have challenge_year=None")
    else:
        print("✓ All transactions now have challenge_year set")


def reverse_backfill(apps, schema_editor):
    """Reverse migration - set challenge_year back to None (optional, for rollback)"""
    SavingsTransaction = apps.get_model('savings_52_weeks', 'SavingsTransaction')
    count = SavingsTransaction.objects.filter(challenge_year__isnull=False).update(challenge_year=None)
    print(f"✓ Reversed challenge_year backfill for {count} transactions")


class Migration(migrations.Migration):

    dependencies = [
        ('savings_52_weeks', '0006_add_challenge_year'),
    ]

    operations = [
        migrations.RunPython(backfill_challenge_year, reverse_backfill),
    ]

