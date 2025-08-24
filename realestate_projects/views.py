from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from accounts.models import UserProfile
from accounts.decorators import verified_required, project_required



@project_required("Real Estate Projects")
def real_estate_projects_dashboard(request):
    return render(request, 'realestate_projects/rep-dashboard.html')



