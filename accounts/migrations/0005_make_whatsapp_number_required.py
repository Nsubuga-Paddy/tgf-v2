# Generated manually for making whatsapp_number required

from django.db import migrations, models
import phonenumber_field.modelfields


def set_default_phone_numbers(apps, schema_editor):
    """Set a temporary phone number for users without one"""
    UserProfile = apps.get_model('accounts', 'UserProfile')
    
    # Find all profiles without phone numbers
    profiles_without_phone = UserProfile.objects.filter(whatsapp_number__isnull=True)
    
    for profile in profiles_without_phone:
        # Generate a temporary unique number based on user ID
        # Format: +256700000000 + user_id (padded to ensure uniqueness)
        # Users will need to update this to their real number
        temp_number = f"+2567000000{profile.user_id:03d}"
        profile.whatsapp_number = temp_number
        profile.save()


def reverse_set_default_phone_numbers(apps, schema_editor):
    """Reverse migration - set phone numbers back to NULL"""
    UserProfile = apps.get_model('accounts', 'UserProfile')
    # Find profiles with temporary numbers (starting with +2567000000)
    UserProfile.objects.filter(whatsapp_number__startswith='+2567000000').update(whatsapp_number=None)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_add_withdrawal_gwc_mesu_models'),
    ]

    operations = [
        # First, set default phone numbers for existing users
        migrations.RunPython(set_default_phone_numbers, reverse_set_default_phone_numbers),
        # Remove the old unique constraint
        migrations.RemoveConstraint(
            model_name='userprofile',
            name='uniq_whatsapp_when_set',
        ),
        # Update the field to be required (no null, no blank)
        migrations.AlterField(
            model_name='userprofile',
            name='whatsapp_number',
            field=phonenumber_field.modelfields.PhoneNumberField(help_text='Include country code, e.g., +2567xxxxxxxx (Required for contact)', max_length=128, region='UG', unique=True),
        ),
        # Add new unique constraint (always enforced since field is required)
        migrations.AddConstraint(
            model_name='userprofile',
            constraint=models.UniqueConstraint(fields=['whatsapp_number'], name='uniq_whatsapp'),
        ),
    ]

