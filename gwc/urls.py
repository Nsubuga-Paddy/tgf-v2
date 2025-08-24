from django.urls import path
from . import views

app_name = 'gwc'

urlpatterns = [
    path("", views.gwc_dashboard, name="gwc"),
]
