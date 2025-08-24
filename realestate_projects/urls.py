from django.urls import path
from . import views

app_name = 'realestate_projects'

urlpatterns = [
    path("", views.real_estate_projects_dashboard, name="rep"),
]
