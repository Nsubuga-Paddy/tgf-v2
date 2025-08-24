from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from accounts.models import UserProfile
from accounts.decorators import verified_required, project_required



@project_required("Clubs Account")
def clubs_account_dashboard(request):
    return render(request, 'clubs_account/clubs-account-dashboard.html')



