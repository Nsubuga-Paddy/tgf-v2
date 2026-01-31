from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from phonenumber_field.formfields import PhoneNumberField
from .models import UserProfile

User = get_user_model()


class PasswordResetRequestForm(forms.Form):
    """
    Form for forgot-password: user enters username, email, or phone number.
    """
    username_email_phone = forms.CharField(
        label="Username, email or phone number",
        max_length=254,
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Enter your username, email or phone (e.g. +2567...)",
            "autofocus": True,
        }),
        help_text="Enter any one: your username, email address, or WhatsApp/phone number.",
    )

    def clean_username_email_phone(self):
        value = (self.cleaned_data.get("username_email_phone") or "").strip()
        if not value:
            raise forms.ValidationError("This field is required.")
        return value


class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True, help_text='Required.')
    last_name = forms.CharField(max_length=30, required=True, help_text='Required.')
    email = forms.EmailField(max_length=254, required=True, help_text='Required.')
    whatsapp_number = PhoneNumberField(
        region="UG",
        required=True,
        help_text='Required. Include country code, e.g., +2567xxxxxxxx'
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'whatsapp_number', 'password1', 'password2')

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['whatsapp_number', 'national_id', 'address', 'bio', 'birthdate', 'photo']
