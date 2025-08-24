from django.urls import path
from . import views

app_name = 'fixed_savings'

urlpatterns = [
    path("", views.individual_fixed_savings_account, name="fsa"),
    path("fsa-terms/", views.fixed_savings_terms, name="fsa_terms"),
]
