from __future__ import annotations

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .emails import send_account_verified_email
from .models import UserProfile


@receiver(pre_save, sender=UserProfile)
def remember_profile_verification_state(sender, instance: UserProfile, **kwargs):
    if instance.pk:
        previous = (
            UserProfile.objects.filter(pk=instance.pk)
            .values_list("is_verified", flat=True)
            .first()
        )
        instance._was_verified = bool(previous)
    else:
        instance._was_verified = False


@receiver(post_save, sender=UserProfile)
def notify_member_on_verification(sender, instance: UserProfile, **kwargs):
    was_verified = getattr(instance, "_was_verified", False)
    if not instance.is_verified or was_verified:
        return
    send_account_verified_email(instance.user)
