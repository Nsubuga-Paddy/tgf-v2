from django.urls import path
from . import views

app_name = 'goat_farming'

urlpatterns = [
    path('', views.cgf_dashboard, name='dashboard'),
    path('investment/', views.investment_page, name='investment'),
    path('investment/<int:investment_id>/details/', views.investment_details, name='investment_details'),
    path('transactions/', views.transactions_page, name='transactions'),
    path('transactions/<int:transaction_id>/details/', views.transaction_details, name='transaction_details'),
    path('tracking/', views.tracking_page, name='tracking'),
]