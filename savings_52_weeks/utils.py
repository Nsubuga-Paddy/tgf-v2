"""
Utility functions for processing interest payments
"""
from django.utils import timezone
from django.db import transaction as db_transaction
from decimal import Decimal
from datetime import date
from .models import Investment, SavingsTransaction


def process_user_matured_investments(user_profile):
    """
    Process interest for all matured investments for a specific user.
    Called when user views their dashboard.
    Returns list of transactions created.
    """
    transactions_created = []
    today = timezone.localdate()
    
    # Get all investments that haven't been paid yet
    # Check both 'matured' status and 'fixed' investments that have reached maturity date
    investments_to_check = Investment.objects.filter(
        user_profile=user_profile,
        interest_paid=False
    )
    
    for investment in investments_to_check:
        # Refresh from database to get latest status
        investment.refresh_from_db()
        
        # Check if investment has reached maturity date
        if investment.maturity_date > today:
            continue  # Not matured yet, skip
        
        # If status is still 'fixed', update it to 'matured' first
        if investment.status == 'fixed':
            investment.status = 'matured'
            investment.save(update_fields=['status'])
            # Refresh again after status update
            investment.refresh_from_db()
        
        try:
            with db_transaction.atomic():
                transaction = investment.process_maturity_interest()
                if transaction:
                    transactions_created.append(transaction)
                    print(f"SUCCESS: Processed interest for investment #{investment.id}: UGX {transaction.amount:,.0f}")
        except Exception as e:
            # Log error but don't break the flow
            print(f"ERROR: Processing investment #{investment.id}: {str(e)}")
            import traceback
            traceback.print_exc()
    
    return transactions_created


def process_user_uninvested_interest(user_profile):
    """
    Process 15% interest on uninvested savings for a user.
    Only processes on Dec 31, 2025.
    Returns transaction if created, None otherwise.
    """
    today = timezone.localdate()
    
    # Only process on Dec 31, 2025
    if today != date(2025, 12, 31):
        return None
    
    # Check if already processed
    existing = SavingsTransaction.objects.filter(
        user_profile=user_profile,
        receipt_number__startswith='UNINV-INT-2025'
    ).exists()
    
    if existing:
        return None
    
    # Calculate uninvested savings
    total_savings = SavingsTransaction.get_user_total_savings(user_profile)
    total_invested = sum(
        inv.amount_invested for inv in user_profile.investments.filter(status='fixed')
    )
    uninvested_amount = total_savings - total_invested
    
    if uninvested_amount <= 0:
        return None
    
    # Calculate 15% interest
    interest_amount = uninvested_amount * Decimal('0.15')
    
    try:
        with db_transaction.atomic():
            interest_transaction = SavingsTransaction.objects.create(
                user_profile=user_profile,
                amount=interest_amount,
                transaction_type='deposit',
                transaction_date=date(2025, 12, 31),
                receipt_number=f'UNINV-INT-2025-{user_profile.id}',
            )
            return interest_transaction
    except Exception as e:
        print(f"Error processing uninvested interest for {user_profile.user.get_username()}: {str(e)}")
        return None


def process_user_challenge_transfer(user_profile):
    """
    Process transfer of all 52WSC 2025 savings to user account.
    Only processes on Jan 1, 2026.
    Returns transaction if created, None otherwise.
    """
    today = timezone.localdate()
    
    # Only process on Jan 1, 2026
    if today != date(2026, 1, 1):
        return None
    
    # Check if already processed
    existing = SavingsTransaction.objects.filter(
        user_profile=user_profile,
        receipt_number__startswith='TRANSFER-2025-'
    ).exists()
    
    if existing:
        return None
    
    # Calculate total savings (including all interest)
    total_savings = SavingsTransaction.get_user_total_savings(user_profile)
    
    if total_savings <= 0:
        return None
    
    try:
        with db_transaction.atomic():
            transfer_transaction = SavingsTransaction.objects.create(
                user_profile=user_profile,
                amount=total_savings,
                transaction_type='deposit',
                transaction_date=date(2026, 1, 1),
                receipt_number=f'TRANSFER-2025-{user_profile.id}-{today.strftime("%Y%m%d")}',
            )
            return transfer_transaction
    except Exception as e:
        print(f"Error processing transfer for {user_profile.user.get_username()}: {str(e)}")
        return None


def process_user_interest_payments(user_profile):
    """
    Main function to process all interest payments for a user.
    Called when user views their dashboard.
    Returns summary of what was processed.
    """
    summary = {
        'investments_processed': 0,
        'uninvested_interest_processed': False,
        'transfer_processed': False,
        'transactions_created': []
    }
    
    # Process matured investments
    investment_transactions = process_user_matured_investments(user_profile)
    summary['investments_processed'] = len(investment_transactions)
    summary['transactions_created'].extend(investment_transactions)
    
    # Process uninvested savings interest (Dec 31, 2025)
    uninvested_transaction = process_user_uninvested_interest(user_profile)
    if uninvested_transaction:
        summary['uninvested_interest_processed'] = True
        summary['transactions_created'].append(uninvested_transaction)
    
    # Process challenge transfer (Jan 1, 2026)
    transfer_transaction = process_user_challenge_transfer(user_profile)
    if transfer_transaction:
        summary['transfer_processed'] = True
        summary['transactions_created'].append(transfer_transaction)
    
    return summary

