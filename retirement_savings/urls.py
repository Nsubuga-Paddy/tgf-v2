from django.urls import path
from . import views

app_name = 'retirement_savings'

urlpatterns = [
    path("", views.retirement_savings_dashboard, name="rss"),
]
