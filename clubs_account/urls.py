from django.urls import path
from . import views

app_name = 'clubs_account'

urlpatterns = [
    path("", views.clubs_account_dashboard, name="clubs_account"),
]
