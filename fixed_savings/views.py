from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from accounts.models import UserProfile
from accounts.decorators import verified_required, project_required


@project_required('Fixed Savings')
def fixed_savings_terms(request):
    return render(request, 'fixed_savings/fsa-terms.html')


@project_required('Fixed Savings')
def individual_fixed_savings_account(request):
    
    return render(request, 'fixed_savings/fsa.html')
