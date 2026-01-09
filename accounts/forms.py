from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from phonenumber_field.formfields import PhoneNumberField
from .models import UserProfile

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
