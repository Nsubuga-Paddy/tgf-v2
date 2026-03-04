from django.urls import path
from . import views

app_name = 'realestate_projects'

urlpatterns = [
    path("", views.real_estate_projects_dashboard, name="rep"),
    path("join/<int:pk>/", views.request_join_project, name="request_join"),
    path("interest/<int:pk>/", views.submit_interest, name="submit_interest"),
    path("<int:pk>/", views.project_detail, name="detail"),
]
