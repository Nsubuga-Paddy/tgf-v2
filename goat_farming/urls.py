from django.urls import path
from . import views

app_name = 'goat_farming'

urlpatterns = [
    path("", views.cgf_dashboard, name="cgf"),
]