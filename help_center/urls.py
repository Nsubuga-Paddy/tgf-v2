from django.urls import path

from .views import HelpCenterView

app_name = "help_center"

urlpatterns = [
    path("", HelpCenterView.as_view(), name="guides"),
]
