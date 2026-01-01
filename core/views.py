# core/views.py
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from accounts.models import UserProfile
from accounts.decorators import verified_required


@method_decorator(login_required, name='dispatch')
@method_decorator(verified_required, name='dispatch')
class LandingPage(TemplateView):
    """
    Landing page that requires user authentication.
    This will be the main dashboard after login.
    """
    template_name = "core/index.html"


class LoginPage(TemplateView):
    """
    Login page template renderer.
    The actual login logic is handled by accounts.views.login_view
    """
    template_name = "core/login.html"


class SignUpPage(TemplateView):
    """
    Signup page template renderer.
    The actual signup logic is handled by accounts.views.signup
    """
    template_name = "core/signup.html"

@method_decorator(login_required, name='dispatch')
class ProfileView(TemplateView):
    template_name = "core/profile.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get user's accessible projects
        if hasattr(user, 'profile'):
            context['user_projects'] = user.profile.projects.all()
        else:
            context['user_projects'] = []
            
        context['user'] = user
        return context
    
    def post(self, request, *args, **kwargs):
        user = request.user
        
        # Update User model fields
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.save()
        
        # Update UserProfile fields
        profile = user.profile
        profile.whatsapp_number = request.POST.get('whatsapp_number', '')
        profile.national_id = request.POST.get('national_id', '')
        profile.address = request.POST.get('address', '')
        profile.bio = request.POST.get('bio', '')
        
        # Handle birthdate
        birthdate = request.POST.get('birthdate')
        if birthdate:
            profile.birthdate = birthdate
        else:
            profile.birthdate = None
        
        # Handle profile photo upload
        if 'photo' in request.FILES:
            profile.photo = request.FILES['photo']
        
        profile.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')


class VerificationPendingView(TemplateView):
    """
    Page shown to users whose accounts are awaiting verification.
    """
    template_name = "core/verification_pending.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context
