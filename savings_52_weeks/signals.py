from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Investment


@receiver(post_save, sender=Investment)
def check_investment_maturity_on_save(sender, instance, created, **kwargs):
    """
    Automatically check and update investment maturity status when saved.
    This ensures that when an investment is created or updated, its status
    is immediately checked against the current date.
    Note: The actual transaction creation for matured interest is handled
    in the check_and_update_status() method to avoid signal recursion.
    """
    if created or instance.status == 'fixed':
        # Check if this investment has matured
        if instance.is_matured:
            # Use check_and_update_status which will handle transaction creation
            instance.check_and_update_status()
